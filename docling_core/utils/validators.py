#
# Copyright IBM Corp. 2024 - 2024
# SPDX-License-Identifier: MIT
#

"""Module for custom type validators."""
import json
import logging
import re
from datetime import datetime
from importlib import resources
from typing import Hashable, TypeVar

import jsonschema
from pydantic_core import PydanticCustomError

from docling_core.types.doc import tokens
from docling_core.types.doc.tokens import DocumentToken

logger = logging.getLogger("docling-core")

T = TypeVar("T", bound=Hashable)


def validate_schema(file_: dict, schema: dict) -> tuple[bool, str]:
    """Check wheter the workflow is properly formatted JSON and contains valid keys.

    Where possible, this also checks a few basic dependencies between properties, but
    this functionality is limited.
    """
    try:
        jsonschema.validate(file_, schema)
        return (True, "All good!")

    except jsonschema.ValidationError as err:
        return (False, err.message)


def validate_raw_schema(file_: dict) -> tuple[bool, str]:
    """Validate a RAW file."""
    logger.debug("validate RAW schema ... ")

    schema_txt = (
        resources.files("docling_core")
        .joinpath("resources/schemas/legacy_doc/RAW.json")
        .read_text("utf-8")
    )
    schema = json.loads(schema_txt)

    return validate_schema(file_, schema)


def validate_ann_schema(file_: dict) -> tuple[bool, str]:
    """Validate an annotated (ANN) file."""
    logger.debug("validate ANN schema ... ")

    schema_txt = (
        resources.files("docling_core")
        .joinpath("resources/schemas/legacy_doc/ANN.json")
        .read_text("utf-8")
    )
    schema = json.loads(schema_txt)

    return validate_schema(file_, schema)


def validate_ocr_schema(file_: dict) -> tuple[bool, str]:
    """Validate an OCR file."""
    logger.debug("validate OCR schema ... ")

    schema_txt = (
        resources.files("docling_core")
        .joinpath("resources/schemas/legacy_doc/OCR-output.json")
        .read_text("utf-8")
    )
    schema = json.loads(schema_txt)

    return validate_schema(file_, schema)


def validate_unique_list(v: list[T]) -> list[T]:
    """Validate that a list has unique values.

    Validator for list types, since pydantic V2 does not support the `unique_items`
    parameter from V1. More information on
    https://github.com/pydantic/pydantic-core/pull/820#issuecomment-1670475909

    Args:
        v: any list of hashable types

    Returns:
        The list, after checking for unique items.
    """
    if len(v) != len(set(v)):
        raise PydanticCustomError("unique_list", "List must be unique")
    return v


def validate_datetime(v, handler):
    """Validate that a value is a datetime or a non-numeric string."""
    if type(v) is datetime or (type(v) is str and not v.isnumeric()):
        return handler(v)
    else:
        raise ValueError("Value type must be a datetime or a non-numeric string")


def validate_doctags(doctags: str):
    terminals = set(DocumentToken.get_special_tokens())
    non_terminals = {
        "DocTags",
        "Body",
        "Content",
        "DocItem",
        "TextItem",
        "TableItem",
        "PictureItem",
        "KeyValueItem",
        "FormItem",
        "TextBody",
        "TextContent",
        "LocTag",
    }
    start_symbol = "DocTags"
    content_symbol = "TextContent"

    text_labels = [
        "caption",
        "checkbox_selected",
        "checkbox_unselected",
        "footnote",
        "page_footer",
        "page_header",
        "paragraph",
        "reference",
        "text",
    ]

    production_rules = {
        "DocTags": [f"<{DocumentToken.DOCUMENT.value}> Body </{DocumentToken.DOCUMENT.value}>"],
        "Body": ["DocItem", "DocItem Body", f"Body <{DocumentToken.PAGE_BREAK.value}> Body"],
        "DocItem": ["TextItem"],
        "TextItem": [
            f"<{DocumentToken.create_token_name_from_doc_item_label(label)}> TextBody </{DocumentToken.create_token_name_from_doc_item_label(label)}>"
            for label in text_labels],
        "TextBody": ["LocTag LocTag LocTag LocTag TextContent"],
        "LocTag": list(filter(lambda tag: tokens._LOC_PREFIX in tag, terminals))
    }

    def _tokenize_production(production):
        return production.split()

    # Validate grammar
    # Check start symbol
    if start_symbol not in non_terminals:
        raise ValueError(f"Start symbol {start_symbol} must be a non-terminal")

    _validate_grammar(_tokenize_production, content_symbol, non_terminals, production_rules, terminals)

    def tokenize_input(text: str):
        token_regex = re.compile(r'|'.join(map(re.escape, sorted(list(terminals), key=len, reverse=True))))
        tokens = []
        pos = 0
        while pos < len(text):
            match = token_regex.match(text, pos)
            if match:
                tokens.append(match.group())
                pos = match.end()
            else:
                while pos < len(text) and not token_regex.match(text, pos):
                    pos += 1
                tokens.append(content_symbol)
        return tokens

    no_whitespace = "".join(doctags.split())
    tokenized_input = tokenize_input(no_whitespace)
    visited = set()

    def recursive_descent(symbol, token_index):
        """
        Performs a recursive descent parsing.

        Args:
            symbol: The current non-terminal symbol to expand.
            token_index: The current index in the token list.

        Returns:
            A tuple (bool, int) indicating whether the symbol can be derived from the remaining tokens,
            and the updated token index.
        """
        if (symbol, token_index) in visited:
            return False, token_index  # Prevent infinite recursion

        visited.add((symbol, token_index))

        if symbol not in production_rules:  # terminal
            if token_index < len(tokenized_input) and tokenized_input[token_index] == symbol:
                return True, token_index + 1
            else:
                return False, token_index

        for production in production_rules[symbol]:
            production_symbols = production.split()
            current_index = token_index
            valid = True

            for prod_symbol in production_symbols:
                valid, current_index = recursive_descent(prod_symbol, current_index)
                if not valid:
                    break

            if valid:
                visited.remove((symbol, token_index))  # remove from visited, since we found a valid path
                return True, current_index

        visited.remove((symbol, token_index))  # remove from visited, since all production rules failed.
        return False, token_index

    valid, final_index = recursive_descent(start_symbol, 0)
    return valid and final_index == len(tokenized_input)


def _validate_grammar(_tokenize_production, content_symbol, non_terminals, production_rules, terminals):
    for nt, prod_list in production_rules.items():
        if nt not in non_terminals:
            raise ValueError(f"Production key {nt} must be a non-terminal")

        for production in prod_list:
            # Split production into symbols
            symbols = _tokenize_production(production)

            # Validate each symbol
            for symbol in symbols:
                if (symbol not in non_terminals and
                        symbol not in terminals and
                        symbol != content_symbol):
                    raise ValueError(f"Invalid symbol {symbol} in production")
