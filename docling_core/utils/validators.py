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
from pyparsing import (
    Forward,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    delimitedList,
    Group,
    Suppress,
)

from docling_core.types.doc import tokens
from docling_core.types.doc.tokens import DocumentToken, TableToken

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


def validate_doctags(input_dt: str):
    def tokenize_input(text: str):
        token_regex = re.compile(
            r"|".join(map(re.escape, sorted(list(terminals), key=len, reverse=True)))
        )
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

    content_symbol = "Content"
    terminals = set(DocumentToken.get_special_tokens())
    terminals.add(content_symbol)

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
        "formula",
        "title",
    ]

    # Non-terminals
    start = Forward()
    body = Forward()
    docitem = Forward()
    textitem = Forward()
    textbody = Forward()
    loctag = Forward()
    tableitem = Forward()
    tablebody = Forward()
    row = Forward()
    cell = Forward()
    page = Forward()
    caption = Forward()
    pictureitem = Forward()
    picclass = Forward()
    smiles = Forward()
    codelang = Forward()
    codebody = Forward()
    orderedlist = Forward()
    unorderedlist = Forward()
    listitem = Forward()
    listitembody = Forward()

    # Grammar
    start <<= (
        Literal(f"<{DocumentToken.DOCUMENT.value}>")
        + body
        + Literal(f"</{DocumentToken.DOCUMENT.value}>")
    )
    page <<= OneOrMore(docitem)
    body <<= delimitedList(page, delim=Literal(f"<{DocumentToken.PAGE_BREAK.value}>"))
    docitem <<= textitem | tableitem | pictureitem | orderedlist | unorderedlist
    text_label_items = (
        [
            Literal(f"<{DocumentToken.create_token_name_from_doc_item_label(label)}>")
            + textbody
            + Literal(
                f"</{DocumentToken.create_token_name_from_doc_item_label(label)}>"
            )
            for label in text_labels
        ]
        + [
            Literal(f"<{tokens._SECTION_HEADER_PREFIX}{i}>")
            + textbody
            + Literal(f"</{tokens._SECTION_HEADER_PREFIX}{i}>")
            for i in range(6)
        ]
        + [
            Literal(f"<{DocumentToken.CODE.value}>")
            + codebody
            + Literal(f"</{DocumentToken.CODE.value}>")
        ]
    )
    textitem <<= MatchFirst(text_label_items)
    textbody <<= Optional(loctag + loctag + loctag + loctag) + Optional(
        Literal(content_symbol)
    )
    codebody <<= Optional(loctag + loctag + loctag + loctag) + Optional(
        codelang + Literal(content_symbol)
    )
    codelang <<= MatchFirst([Literal(lang.value) for lang in tokens._CodeLanguageToken])
    loctags = list(
        map(
            lambda x: Literal(x),
            filter(lambda tag: tokens._LOC_PREFIX in tag, terminals),
        )
    )
    loctag <<= MatchFirst(loctags)

    tableitem <<= (
        Literal("<otsl>")
        + Optional(loctag + loctag + loctag + loctag)
        + Optional(tablebody)
        + Optional(Literal(TableToken.OTSL_NL.value) + caption)
        + Literal("</otsl>")
    )
    caption <<= (
        Literal("<caption>")
        + Optional(loctag + loctag + loctag + loctag)
        + Optional(Literal(content_symbol))
        + Literal("</caption>")
    )
    tablebody <<= row + Optional(Literal(TableToken.OTSL_NL.value) + tablebody)
    row <<= OneOrMore(cell)
    celltags = [
        Literal(tok) + Optional(Literal(content_symbol))
        for tok in TableToken.get_special_tokens()
        if tok != TableToken.OTSL_NL.value
    ]
    cell <<= MatchFirst(celltags)

    pictureitem <<= (
        Literal(f"<{DocumentToken.PICTURE.value}>")
        + Optional(loctag + loctag + loctag + loctag)
        + Optional(picclass)
        + Optional(smiles)
        + Optional(caption)
        + Literal(f"</{DocumentToken.PICTURE.value}>")
    )
    picclass <<= MatchFirst(
        [Literal(pclass.value) for pclass in tokens._PictureClassificationToken]
    )
    smiles <<= (
        Literal(f"<{DocumentToken.SMILES.value}>")
        + Literal(content_symbol)
        + Literal(f"</{DocumentToken.SMILES.value}>")
    )

    orderedlist <<= Group(
        Suppress(Literal(f"<{DocumentToken.ORDERED_LIST.value}>"))
        + OneOrMore(listitem)
        + Suppress(Literal(f"</{DocumentToken.ORDERED_LIST.value}>"))
    )
    unorderedlist <<= Group(
        Suppress(Literal(f"<{DocumentToken.UNORDERED_LIST.value}>"))
        + OneOrMore(listitem)
        + Suppress(Literal(f"</{DocumentToken.UNORDERED_LIST.value}>"))
    )
    listitem << Group(
        Suppress(Literal(f"<{DocumentToken.LIST_ITEM.value}>"))
        + listitembody
        + Suppress(Literal(f"</{DocumentToken.LIST_ITEM.value}>"))
    )
    listitembody <<= orderedlist | unorderedlist | textbody

    def is_valid(s):
        try:
            start.parseString(s, parseAll=True)
            return True
        except Exception as e:
            print(e)
            return False

    def preprocess(input_dt):
        return "".join(tokenize_input("".join(input_dt.split())))

    listitembody.setDebug()
    processed_input = preprocess(input_dt)

    return is_valid(processed_input)
