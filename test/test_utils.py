#
# Copyright IBM Corp. 2024 - 2024
# SPDX-License-Identifier: MIT
#

"""Test the pydantic models in package utils."""
import json

from pydantic import Field
from requests import Response

from docling_core.utils.alias import AliasModel
from docling_core.utils.file import resolve_source_to_path, resolve_source_to_stream
from docling_core.utils.validators import validate_doctags


def test_alias_model():
    """Test the functionality of AliasModel."""

    class AliasModelChild(AliasModel):
        foo: str = Field(alias="boo")

    data = {"foo": "lorem ipsum"}
    data_alias = {"boo": "lorem ipsum"}

    # data validated from dict, JSON, and constructor can use field names or aliases

    AliasModelChild.model_validate(data_alias)
    AliasModelChild.model_validate(data)

    AliasModelChild.model_validate_json(json.dumps(data_alias))
    AliasModelChild.model_validate_json(json.dumps(data))

    AliasModelChild(boo="lorem ipsum")
    AliasModelChild(foo="lorem ipsum")

    # children classes will also inherite the populate_by_name

    class AliasModelGrandChild(AliasModelChild):
        var: int

    AliasModelGrandChild(boo="lorem ipsum", var=3)
    AliasModelGrandChild(foo="lorem ipsum", var=3)

    # serialized data will always use aliases

    obj = AliasModelChild.model_validate(data_alias)
    assert obj.model_dump() == data_alias
    assert obj.model_dump() != data

    assert obj.model_dump_json() == json.dumps(data_alias, separators=(",", ":"))
    assert obj.model_dump_json() != json.dumps(data, separators=(",", ":"))


def test_resolve_source_to_path_url_wout_path(monkeypatch):
    expected_str = "foo"
    expected_bytes = bytes(expected_str, "utf-8")

    def get_dummy_response(*args, **kwargs):
        r = Response()
        r.status_code = 200
        r._content = expected_bytes
        return r

    monkeypatch.setattr("requests.get", get_dummy_response)
    monkeypatch.setattr(
        "requests.models.Response.iter_content",
        lambda *args, **kwargs: [expected_bytes],
    )
    path = resolve_source_to_path("https://pypi.org")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert text == expected_str


def test_resolve_source_to_stream_url_wout_path(monkeypatch):
    expected_str = "foo"
    expected_bytes = bytes(expected_str, "utf-8")

    def get_dummy_response(*args, **kwargs):
        r = Response()
        r.status_code = 200
        r._content = expected_bytes
        return r

    monkeypatch.setattr("requests.get", get_dummy_response)
    monkeypatch.setattr(
        "requests.models.Response.iter_content",
        lambda *args, **kwargs: [expected_bytes],
    )
    doc_stream = resolve_source_to_stream("https://pypi.org")
    assert doc_stream.name == "file"

    text = doc_stream.stream.read().decode("utf8")
    assert text == expected_str


def test_validate_doctags():
    #     doctags = """<doctag><text><loc_42><loc_26><loc_406><loc_46>DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis</text>
    # </doctag>"""
    doctags = """<doctag><page_header><loc_15><loc_104><loc_30><loc_350>arXiv:2206.01062v1  [cs.CV]  2 Jun 2022</page_header>
<section_header_level_1><loc_88><loc_53><loc_413><loc_75>DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis</section_header_level_1>
<text><loc_74><loc_85><loc_158><loc_114>Birgit Pfitzmann IBM Research Rueschlikon, Switzerland bpf@zurich.ibm.com</text>
<page_break>
<page_header><loc_44><loc_38><loc_456><loc_43>KDD '22, August 14-18, 2022, Washington, DC, USA Birgit Pfitzmann, Christoph Auer, Michele Dolfi, Ahmed S. Nassar, and Peter Staar</page_header>
<otsl><loc_81><loc_87><loc_419><loc_186><ecel><ecel><ched>% of Total<lcel><lcel><lcel><ched>triple inter-annotator mAP @ 0.5-0.95 (%)<lcel><lcel><lcel><lcel><lcel><nl><ched>class label<ched>Count<ched>Train<ched>Test<ched>Val<ched>All<ched>Fin<ched>Man<ched>Sci<ched>Law<ched>Pat<ched>Ten<nl><rhed>Caption<fcel>22524<fcel>2.04<fcel>1.77<fcel>2.32<fcel>84-89<fcel>40-61<fcel>86-92<fcel>94-99<fcel>95-99<fcel>69-78<fcel>n/a<nl><rhed>Footnote<fcel>6318<fcel>0.60<fcel>0.31<fcel>0.58<fcel>83-91<fcel>n/a<fcel>100<fcel>62-88<fcel>85-94<fcel>n/a<fcel>82-97<nl><rhed>Formula<fcel>25027<fcel>2.25<fcel>1.90<fcel>2.96<fcel>83-85<fcel>n/a<fcel>n/a<fcel>84-87<fcel>86-96<fcel>n/a<fcel>n/a<nl><rhed>List-item<fcel>185660<fcel>17.19<fcel>13.34<fcel>15.82<fcel>87-88<fcel>74-83<fcel>90-92<fcel>97-97<fcel>81-85<fcel>75-88<fcel>93-95<nl><rhed>Page-footer<fcel>70878<fcel>6.51<fcel>5.58<fcel>6.00<fcel>93-94<fcel>88-90<fcel>95-96<fcel>100<fcel>92-97<fcel>100<fcel>96-98<nl><rhed>Page-header<fcel>58022<fcel>5.10<fcel>6.70<fcel>5.06<fcel>85-89<fcel>66-76<fcel>90-94<fcel>98-100<fcel>91-92<fcel>97-99<fcel>81-86<nl><rhed>Picture<fcel>45976<fcel>4.21<fcel>2.78<fcel>5.31<fcel>69-71<fcel>56-59<fcel>82-86<fcel>69-82<fcel>80-95<fcel>66-71<fcel>59-76<nl><rhed>Section-header<fcel>142884<fcel>12.60<fcel>15.77<fcel>12.85<fcel>83-84<fcel>76-81<fcel>90-92<fcel>94-95<fcel>87-94<fcel>69-73<fcel>78-86<nl><rhed>Table<fcel>34733<fcel>3.20<fcel>2.27<fcel>3.60<fcel>77-81<fcel>75-80<fcel>83-86<fcel>98-99<fcel>58-80<fcel>79-84<fcel>70-85<nl><rhed>Text<fcel>510377<fcel>45.82<fcel>49.28<fcel>45.00<fcel>84-86<fcel>81-86<fcel>88-93<fcel>89-93<fcel>87-92<fcel>71-79<fcel>87-95<nl><rhed>Title<fcel>5071<fcel>0.47<fcel>0.30<fcel>0.50<fcel>60-72<fcel>24-63<fcel>50-63<fcel>94-100<fcel>82-96<fcel>68-79<fcel>24-56<nl><rhed>Total<fcel>1107470<fcel>941123<fcel>99816<fcel>66531<fcel>82-83<fcel>71-74<fcel>79-81<fcel>89-94<fcel>86-91<fcel>71-76<fcel>68-85<nl><caption><loc_44><loc_54><loc_456><loc_73>Table 1: DocLayNet dataset overview. Along with the frequency of each class label, we present the relative occurrence (as % of row 'Total') in the train, test and validation sets. The inter-annotator agreement is computed as the mAP@0.5-0.95 metric between pairwise annotations from the triple-annotated pages, from which we obtain accuracy ranges.</caption></otsl>
</doctag>
    """
    #
    #     doctags = """<doctag>
    # <otsl><loc_81><loc_87><loc_419><loc_186><ecel><ecel><ched>% of Total<lcel><lcel><lcel><ched>triple inter-annotator mAP @ 0.5-0.95 (%)<lcel><lcel><lcel><lcel><lcel><nl><ched>class label<ched>Count<ched>Train<ched>Test<ched>Val<ched>All<ched>Fin<ched>Man<ched>Sci<ched>Law<ched>Pat<ched>Ten<nl><rhed>Caption<fcel>22524<fcel>2.04<fcel>1.77<fcel>2.32<fcel>84-89<fcel>40-61<fcel>86-92<fcel>94-99<fcel>95-99<fcel>69-78<fcel>n/a<nl><rhed>Footnote<fcel>6318<fcel>0.60<fcel>0.31<fcel>0.58<fcel>83-91<fcel>n/a<fcel>100<fcel>62-88<fcel>85-94<fcel>n/a<fcel>82-97<nl><rhed>Formula<fcel>25027<fcel>2.25<fcel>1.90<fcel>2.96<fcel>83-85<fcel>n/a<fcel>n/a<fcel>84-87<fcel>86-96<fcel>n/a<fcel>n/a<nl><rhed>List-item<fcel>185660<fcel>17.19<fcel>13.34<fcel>15.82<fcel>87-88<fcel>74-83<fcel>90-92<fcel>97-97<fcel>81-85<fcel>75-88<fcel>93-95<nl><rhed>Page-footer<fcel>70878<fcel>6.51<fcel>5.58<fcel>6.00<fcel>93-94<fcel>88-90<fcel>95-96<fcel>100<fcel>92-97<fcel>100<fcel>96-98<nl><rhed>Page-header<fcel>58022<fcel>5.10<fcel>6.70<fcel>5.06<fcel>85-89<fcel>66-76<fcel>90-94<fcel>98-100<fcel>91-92<fcel>97-99<fcel>81-86<nl><rhed>Picture<fcel>45976<fcel>4.21<fcel>2.78<fcel>5.31<fcel>69-71<fcel>56-59<fcel>82-86<fcel>69-82<fcel>80-95<fcel>66-71<fcel>59-76<nl><rhed>Section-header<fcel>142884<fcel>12.60<fcel>15.77<fcel>12.85<fcel>83-84<fcel>76-81<fcel>90-92<fcel>94-95<fcel>87-94<fcel>69-73<fcel>78-86<nl><rhed>Table<fcel>34733<fcel>3.20<fcel>2.27<fcel>3.60<fcel>77-81<fcel>75-80<fcel>83-86<fcel>98-99<fcel>58-80<fcel>79-84<fcel>70-85<nl><rhed>Text<fcel>510377<fcel>45.82<fcel>49.28<fcel>45.00<fcel>84-86<fcel>81-86<fcel>88-93<fcel>89-93<fcel>87-92<fcel>71-79<fcel>87-95<nl><rhed>Title<fcel>5071<fcel>0.47<fcel>0.30<fcel>0.50<fcel>60-72<fcel>24-63<fcel>50-63<fcel>94-100<fcel>82-96<fcel>68-79<fcel>24-56<nl><rhed>Total<fcel>1107470<fcel>941123<fcel>99816<fcel>66531<fcel>82-83<fcel>71-74<fcel>79-81<fcel>89-94<fcel>86-91<fcel>71-76<fcel>68-85</otsl>
    # </doctag>
    #     """
    #
    #     doctags = """<doctag>
    # <otsl><loc_81><loc_87><loc_419><loc_186><ecel><ecel><ched>% of Total<lcel><lcel><lcel><ched>triple inter-annotator mAP @ 0.5-0.95 (%)<lcel><lcel><lcel><lcel><lcel><nl><ched>class label<ched>Count<ched>Train<ched>Test<ched>Val<ched>All<ched>Fin<ched>Man<ched>Sci<ched>Law<ched>Pat<ched>Ten<nl><rhed>Caption<fcel>22524<fcel>2.04<fcel>1.77<fcel>2.32<fcel>84-89<fcel>40-61<fcel>86-92<fcel>94-99<fcel>95-99<fcel>69-78<fcel>n/a<nl><rhed>Footnote<fcel>6318<fcel>0.60<fcel>0.31<fcel>0.58<fcel>83-91<fcel>n/a<fcel>100<fcel>62-88<fcel>85-94<fcel>n/a<fcel>82-97<nl><rhed>Formula<fcel>25027<fcel>2.25<fcel>1.90<fcel>2.96<fcel>83-85<fcel>n/a<fcel>n/a<fcel>84-87<fcel>86-96<fcel>n/a<fcel>n/a<nl><rhed>List-item<fcel>185660<fcel>17.19<fcel>13.34<fcel>15.82<fcel>87-88<fcel>74-83<fcel>90-92<fcel>97-97<fcel>81-85<fcel>75-88<fcel>93-95<nl><rhed>Page-footer<fcel>70878<fcel>6.51<fcel>5.58<fcel>6.00<fcel>93-94<fcel>88-90<fcel>95-96<fcel>100<fcel>92-97<fcel>100<fcel>96-98<nl><rhed>Page-header<fcel>58022<fcel>5.10<fcel>6.70<fcel>5.06<fcel>85-89<fcel>66-76<fcel>90-94<fcel>98-100<fcel>91-92<fcel>97-99<fcel>81-86<nl><rhed>Picture<fcel>45976<fcel>4.21<fcel>2.78<fcel>5.31<fcel>69-71<fcel>56-59<fcel>82-86<fcel>69-82<fcel>80-95<fcel>66-71<fcel>59-76<nl><rhed>Section-header<fcel>142884<fcel>12.60<fcel>15.77<fcel>12.85<fcel>83-84<fcel>76-81<fcel>90-92<fcel>94-95<fcel>87-94<fcel>69-73<fcel>78-86<nl><rhed>Table<fcel>34733<fcel>3.20<fcel>2.27<fcel>3.60<fcel>77-81<fcel>75-80<fcel>83-86<fcel>98-99<fcel>58-80<fcel>79-84<fcel>70-85<nl><rhed>Text<fcel>510377<fcel>45.82<fcel>49.28<fcel>45.00<fcel>84-86<fcel>81-86<fcel>88-93<fcel>89-93<fcel>87-92<fcel>71-79<fcel>87-95<nl><rhed>Title<fcel>5071<fcel>0.47<fcel>0.30<fcel>0.50<fcel>60-72<fcel>24-63<fcel>50-63<fcel>94-100<fcel>82-96<fcel>68-79<fcel>24-56<nl><rhed>Total<fcel>1107470<fcel>941123<fcel>99816<fcel>66531<fcel>82-83<fcel>71-74<fcel>79-81<fcel>89-94<fcel>86-91<fcel>71-76<fcel>68-85<nl><caption><loc_44><loc_54><loc_456><loc_73>Table 1: DocLayNet dataset overview. Along with the frequency of each class label, we present the relative occurrence (as % of row 'Total') in the train, test and validation sets. The inter-annotator agreement is computed as the mAP@0.5-0.95 metric between pairwise annotations from the triple-annotated pages, from which we obtain accuracy ranges.</caption></otsl>
    # </doctag>
    #     """
    #     doctags = """<doctag><page_header><loc_15><loc_104><loc_30><loc_350>arXiv:2206.01062v1  [cs.CV]  2 Jun 2022</page_header>
    # <text><loc_74><loc_85><loc_158><loc_114>Birgit Pfitzmann IBM Research Rueschlikon, Switzerland bpf@zurich.ibm.com</text>
    # <section_header_level_1><loc_88><loc_53><loc_413><loc_75>DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis</section_header_level_1>
    # </doctag>"""
    assert validate_doctags(doctags) == True
