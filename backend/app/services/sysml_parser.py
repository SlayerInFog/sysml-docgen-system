import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedElement:
    uid: str
    name: str
    type: str
    documentation: str | None = None
    parent_uid: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedRelation:
    source_uid: str
    target_uid: str
    relation_type: str
    label: str | None = None


@dataclass
class ParsedModel:
    elements: list[ParsedElement]
    relations: list[ParsedRelation]


ID_KEYS = ("id", "_id", "elementId", "xmi:id", "{http://www.omg.org/XMI}id")
NAME_KEYS = ("name", "title", "qualifiedName")
TYPE_KEYS = ("type", "_type", "xmi:type", "{http://www.omg.org/XMI}type")
DOC_KEYS = ("documentation", "description", "body", "value")
PARENT_KEYS = ("ownerId", "parentId", "parent_uid", "owner", "package")
RELATION_KEYS = (
    "source",
    "target",
    "sourceId",
    "targetId",
    "clientId",
    "supplierId",
    "from",
    "to",
)


# 根据文件类型选择模型解析方式。
def parse_model_file(path: Path) -> ParsedModel:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".json", ".mms"}:
        return parse_json_model(text)
    if suffix in {".xml", ".xmi", ".uml", ".sysml"}:
        return parse_xml_model(text)
    try:
        return parse_json_model(text)
    except Exception:
        return parse_xml_model(text)


# 解析 JSON 格式的模型数据。
def parse_json_model(text: str) -> ParsedModel:
    data = json.loads(text)
    candidates: list[dict[str, Any]] = []

    if isinstance(data, dict):
        if isinstance(data.get("elements"), list):
            candidates.extend([x for x in data["elements"] if isinstance(x, dict)])
        else:
            walk_json(data, candidates)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                walk_json(item, candidates)

    elements: dict[str, ParsedElement] = {}
    relations: list[ParsedRelation] = []
    for item in candidates:
        uid = first_value(item, ID_KEYS)
        if not uid:
            continue
        uid = str(uid)
        element_type = str(first_value(item, TYPE_KEYS) or infer_type(item))
        name = str(first_value(item, NAME_KEYS) or uid)
        documentation = stringify(first_value(item, DOC_KEYS))
        parent_uid = stringify(first_value(item, PARENT_KEYS))

        elements[uid] = ParsedElement(
            uid=uid,
            name=name,
            type=simplify_type(element_type),
            documentation=documentation,
            parent_uid=parent_uid,
            raw=item,
        )

        relation = relation_from_json(item)
        if relation:
            relations.append(relation)

        for key, value in item.items():
            if key.endswith("Ids") and isinstance(value, list):
                rel_type = key[:-3]
                for target in value:
                    relations.append(ParsedRelation(uid, str(target), rel_type, rel_type))

    add_containment_relations(elements, relations)
    return ParsedModel(list(elements.values()), dedupe_relations(relations))


# 解析 XML/XMI 格式的模型数据。
def parse_xml_model(text: str) -> ParsedModel:
    root = ET.fromstring(text)
    elements: dict[str, ParsedElement] = {}
    relations: list[ParsedRelation] = []

    # 处理 visit 相关逻辑。
    def visit(node: ET.Element, parent_uid: str | None = None) -> None:
        attrs = normalize_attrs(node.attrib)
        uid = attrs.get("id") or attrs.get("xmi:id")
        node_type = attrs.get("type") or attrs.get("xmi:type") or strip_namespace(node.tag)
        name = attrs.get("name") or uid or strip_namespace(node.tag)
        doc = attrs.get("documentation") or attrs.get("description")

        current_uid = parent_uid
        if uid:
            current_uid = uid
            elements[uid] = ParsedElement(
                uid=uid,
                name=name,
                type=simplify_type(node_type),
                documentation=doc,
                parent_uid=parent_uid,
                raw=attrs,
            )

            for key, value in attrs.items():
                if key in {"supplier", "client", "type", "href"} or key.endswith("Id"):
                    for target in split_refs(value):
                        if target != uid:
                            relations.append(ParsedRelation(uid, target, key, key))

        for child in node:
            visit(child, current_uid)

    visit(root)
    add_containment_relations(elements, relations)
    return ParsedModel(list(elements.values()), dedupe_relations(relations))


# 递归展开 JSON 模型节点。
def walk_json(item: dict[str, Any], results: list[dict[str, Any]]) -> None:
    if any(key in item for key in ID_KEYS):
        results.append(item)
    for value in item.values():
        if isinstance(value, dict):
            walk_json(value, results)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict):
                    walk_json(child, results)


# 处理 first_value 相关逻辑。
def first_value(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


# 处理 stringify 相关逻辑。
def stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


# 处理 infer_type 相关逻辑。
def infer_type(item: dict[str, Any]) -> str:
    if "appliedStereotypeIds" in item:
        return "StereotypedElement"
    if "ownedAttribute" in item:
        return "Block"
    return "Element"


# 处理 simplify_type 相关逻辑。
def simplify_type(value: str) -> str:
    value = strip_namespace(value)
    if ":" in value:
        value = value.split(":")[-1]
    return value or "Element"


# 处理 strip_namespace 相关逻辑。
def strip_namespace(value: str) -> str:
    return value.split("}", 1)[-1] if "}" in value else value


# 处理 normalize_attrs 相关逻辑。
def normalize_attrs(attrs: dict[str, str]) -> dict[str, str]:
    normalized = {}
    for key, value in attrs.items():
        short = strip_namespace(key)
        normalized[short] = value
        normalized[key] = value
    return normalized


# 处理 split_refs 相关逻辑。
def split_refs(value: str) -> list[str]:
    return [part.strip("# ") for part in re.split(r"[\s,]+", value) if part.strip("# ")]


# 从 JSON 节点中提取关系。
def relation_from_json(item: dict[str, Any]) -> ParsedRelation | None:
    source = first_value(item, ("source", "sourceId", "clientId", "from"))
    target = first_value(item, ("target", "targetId", "supplierId", "to"))
    if source and target:
        return ParsedRelation(
            source_uid=str(source),
            target_uid=str(target),
            relation_type=str(first_value(item, TYPE_KEYS) or "Dependency"),
            label=stringify(first_value(item, NAME_KEYS)),
        )
    return None


# 补充元素父子包含关系。
def add_containment_relations(elements: dict[str, ParsedElement], relations: list[ParsedRelation]) -> None:
    for element in elements.values():
        if element.parent_uid and element.parent_uid in elements:
            relations.append(
                ParsedRelation(
                    source_uid=element.parent_uid,
                    target_uid=element.uid,
                    relation_type="containment",
                    label="contains",
                )
            )


# 去除重复的模型关系。
def dedupe_relations(relations: list[ParsedRelation]) -> list[ParsedRelation]:
    seen: set[tuple[str, str, str]] = set()
    result: list[ParsedRelation] = []
    for relation in relations:
        key = (relation.source_uid, relation.target_uid, relation.relation_type)
        if relation.source_uid and relation.target_uid and key not in seen:
            seen.add(key)
            result.append(relation)
    return result
