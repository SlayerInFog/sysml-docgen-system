# OpenMBEE Interface Adapter

本项目新增了一个轻量级 OpenMBEE 接口适配层，用于保留 OpenMBEE MMS / Doc Convert 的接口契约，方便后续接入真实 MMS 服务。

来源参考：

- `E:\sysml\exec-ve\src\ve-utils\mms-api-client\URL.service.ts`
- `E:\sysml\mms-doc-convert\openapi.yaml`
- OpenMBEE 相关代码许可证：Apache License 2.0

## 后端文件

- `backend/app/services/openmbee_client.py`
- `backend/app/api/openmbee.py`
- `backend/app/schemas/openmbee.py`

## 配置项

在 `backend/.env` 中配置：

```env
OPENMBEE_MMS_URL=http://127.0.0.1:8080
OPENMBEE_MMS_TOKEN=
OPENMBEE_DOC_CONVERT_URL=http://127.0.0.1:8080
```

如果没有部署 MMS，也可以不配置。此时 `/api/openmbee/mms/endpoints` 仍然能返回接口目录，但代理访问接口会提示未配置 MMS 地址。

## 已保留的核心接口契约

```text
GET  /mmsversion
POST /authentication
GET  /permissions
GET  /orgs
GET  /projects
GET  /projects/{projectId}
GET  /projects/{projectId}/refs
GET  /projects/{projectId}/refs/{refId}
GET  /projects/{projectId}/refs/{refId}/commits
GET  /projects/{projectId}/refs/{refId}/elements/{elementId}
GET  /projects/{projectId}/refs/{refId}/views/{elementId}
POST /projects/{projectId}/refs/{refId}/elements
POST /projects/{projectId}/refs/{refId}/views
GET  /projects/{projectId}/refs/{refId}/search
POST /convert
```

## 本系统暴露的适配接口

```text
GET /api/openmbee/config
GET /api/openmbee/mms/endpoints
GET /api/openmbee/mms/version
GET /api/openmbee/mms/projects
GET /api/openmbee/mms/projects/{project_id}/refs
GET /api/openmbee/mms/projects/{project_id}/refs/{ref_id}/elements/{element_id}
GET /api/openmbee/mms/projects/{project_id}/refs/{ref_id}/search
POST /api/openmbee/mms/import
```

`POST /api/openmbee/mms/import` 可以在配置真实 MMS 后，将 MMS 返回的元素数据转换为本系统的 `SysMLModel`、`ModelElement`、`ModelRelation` 记录，形成一个新的本地模型版本。

## 前端入口

入口位于：

```text
模型管理 -> 模型导入来源 -> OpenMBEE MMS
```

当前支持：

```text
测试 MMS 连接
获取 MMS 项目
获取 MMS 分支
按根元素 ID 递归导入
按搜索关键词导入
导入为本系统模型版本
```

这些接口是“OpenMBEE MMS 接入层”，不等于本项目已经完整实现 MMS 服务端。真实数据仍需要外部 MMS 提供。
