from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class OpenMbeeEndpoint:
    name: str
    method: str
    path: str
    description: str


class OpenMbeeClientError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class OpenMbeeMmsUrls:
    def __init__(self, root: str):
        self.root = root.rstrip("/")

    def mms_version(self) -> str:
        return f"{self.root}/mmsversion"

    def projects(self, org_id: str | None = None) -> str:
        url = f"{self.root}/projects"
        return add_params(url, {"orgId": org_id}) if org_id else url

    def refs(self, project_id: str) -> str:
        return f"{self.root}/projects/{project_id}/refs"

    def element(self, project_id: str, ref_id: str, element_id: str, commit_id: str | None = None) -> str:
        return add_version(f"{self.root}/projects/{project_id}/refs/{ref_id}/elements/{element_id}", commit_id)

    def owned_element(
        self,
        project_id: str,
        ref_id: str,
        element_id: str,
        commit_id: str | None = None,
        depth: int | None = None,
    ) -> str:
        url = self.element(project_id, ref_id, element_id, commit_id)
        return add_params(url, {"depth": depth} if depth else {"recurse": "true"})

    def search(self, project_id: str, ref_id: str, params: dict[str, Any] | None = None) -> str:
        return add_params(f"{self.root}/projects/{project_id}/refs/{ref_id}/search", params or {})


class OpenMbeeMmsClient:
    def __init__(self, root: str | None, token: str | None = None, timeout: int = 20):
        self.root = root.rstrip("/") if root else None
        self.token = token
        self.timeout = timeout
        self.urls = OpenMbeeMmsUrls(self.root) if self.root else None

    def require_urls(self) -> OpenMbeeMmsUrls:
        if not self.urls:
            raise OpenMbeeClientError("未配置 OPENMBEE_MMS_URL，无法连接 MMS", 503)
        return self.urls

    def get(self, url: str) -> Any:
        return self.request("GET", url)

    def request(self, method: str, url: str, body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(url=url, data=data, method=method)
        request.add_header("Accept", "application/json")
        request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return json.loads(raw.decode("utf-8"))
                text = raw.decode("utf-8", errors="replace")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"raw": text}
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise OpenMbeeClientError(detail or error.reason, error.code) from error
        except URLError as error:
            raise OpenMbeeClientError(f"MMS 连接失败：{error.reason}", 502) from error


def endpoint_catalog() -> list[OpenMbeeEndpoint]:
    return [
        OpenMbeeEndpoint("mmsVersion", "GET", "/mmsversion", "MMS 版本信息"),
        OpenMbeeEndpoint("projects", "GET", "/projects?orgId={orgId}", "项目列表"),
        OpenMbeeEndpoint("refs", "GET", "/projects/{projectId}/refs", "分支/引用列表"),
        OpenMbeeEndpoint("element", "GET", "/projects/{projectId}/refs/{refId}/elements/{elementId}", "元素详情"),
        OpenMbeeEndpoint("search", "GET", "/projects/{projectId}/refs/{refId}/search", "元素检索"),
        OpenMbeeEndpoint("docConvert", "POST", "/convert", "HTML/CSS 转 docx、pdf 或 latex"),
    ]


def add_version(url: str, commit_id: str | None) -> str:
    if commit_id and commit_id != "latest":
        return add_params(url, {"commitId": commit_id})
    return url


def add_params(url: str, params: dict[str, Any]) -> str:
    clean = {key: value for key, value in params.items() if value is not None}
    if not clean:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(clean)}"


def extract_mms_elements(payload: Any) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        if looks_like_element(value):
            uid = element_uid(value)
            if uid:
                found[uid] = value
        for key in ("elements", "items", "results", "data", "_contents", "contents", "children", "ownedElements"):
            child = value.get(key)
            if child is not None:
                visit(child)

    visit(payload)
    return list(found.values())


def normalize_mms_element(element: dict[str, Any]) -> dict[str, str | None]:
    uid = element_uid(element) or "unknown"
    return {
        "uid": uid,
        "name": first_text(element, ("name", "_name", "title", "qualifiedName")) or uid,
        "type": first_text(element, ("type", "_type", "@type", "classifier")) or "Element",
        "documentation": first_text(element, ("documentation", "_documentation", "description", "body")),
        "parent_uid": first_id(element, ("ownerId", "_ownerId", "parentId", "_parentId", "owner", "parent")),
    }


def extract_mms_relations(elements: list[dict[str, Any]]) -> list[dict[str, str | None]]:
    uid_set = {element_uid(element) for element in elements if element_uid(element)}
    relations: dict[tuple[str, str, str], dict[str, str | None]] = {}
    relation_keys = (
        "contains",
        "ownedElement",
        "ownedElements",
        "children",
        "supplier",
        "client",
        "source",
        "target",
        "relatedElement",
        "relatedElements",
        "valueIds",
    )

    for element in elements:
        source = element_uid(element)
        if not source:
            continue
        parent = first_id(element, ("ownerId", "_ownerId", "parentId", "_parentId", "owner", "parent"))
        if parent and parent in uid_set:
            key = (parent, source, "owner")
            relations[key] = {"source_uid": parent, "target_uid": source, "relation_type": "owner", "label": "owner"}

        for relation_key in relation_keys:
            for target in ids_from_value(element.get(relation_key)):
                if target in uid_set and target != source:
                    key = (source, target, relation_key)
                    relations[key] = {
                        "source_uid": source,
                        "target_uid": target,
                        "relation_type": relation_key[:80],
                        "label": relation_key,
                    }

    return list(relations.values())


def looks_like_element(value: dict[str, Any]) -> bool:
    return bool(element_uid(value)) and any(key in value for key in ("type", "_type", "@type", "name", "_name", "documentation"))


def element_uid(value: dict[str, Any]) -> str | None:
    return first_text(value, ("id", "_id", "elementId", "element_id", "uid", "uuid", "sysmlid", "sysml_id"))


def first_text(value: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        item = value.get(key)
        text = scalar_to_id(item)
        if text:
            return text
    return None


def first_id(value: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        ids = ids_from_value(value.get(key))
        if ids:
            return ids[0]
    return None


def ids_from_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        ids: list[str] = []
        for item in value:
            text = scalar_to_id(item)
            if text:
                ids.append(text)
        return ids
    text = scalar_to_id(value)
    return [text] if text else []


def scalar_to_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return text or None
    if isinstance(value, dict):
        for key in ("id", "_id", "elementId", "element_id", "uid", "value"):
            text = scalar_to_id(value.get(key))
            if text:
                return text
    return None
