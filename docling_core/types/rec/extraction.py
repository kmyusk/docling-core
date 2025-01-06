#
# Copyright IBM Corp. 2024 - 2024
# SPDX-License-Identifier: MIT
#
from __future__ import annotations

from typing import Union

from pydantic import BaseModel

from docling_core.types.doc import DocumentOrigin


class ExtractionTree(BaseModel):
    origin: DocumentOrigin
    content: list[Union[Node, Leaf]]


class Node(BaseModel):
    key: str
    children: list[Union[Node, Leaf]]


class Leaf(BaseModel):
    key: str
    value: str
    page_no: int
