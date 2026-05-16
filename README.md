# 基于 SysML 模型的文档自动生成系统

本项目是重新实现的课程设计系统，参考 OpenMBEE 的 MMS、VE、MDK、DocGen 思路，但采用轻量化 B/S 架构实现。

## 技术栈

- 前端：Vue 3 + Vite + Pinia + Element Plus + Axios
- 后端：Python + FastAPI + SQLAlchemy
- 数据库：MySQL 8，默认 `root/mysql`
- 文档导出：HTML 原生预览，DOCX 使用 `python-docx`，PDF 使用 `reportlab`

## 主要功能

- 用户注册、登录、JWT 鉴权
- 角色权限：管理员、编辑者、读者
- 项目管理
- SysML/XMI/XML/JSON 模型上传与解析
- 模型元素与关系展示
- 模型元素轻量编辑
- 文档模板管理
- 基于模型和模板自动生成文档
- HTML/DOCX/PDF 导出
- 操作日志审计

## 数据库

默认连接：

```text
mysql+pymysql://root:mysql@127.0.0.1:3306/sysml_docgen?charset=utf8mb4
```

如果数据库不存在，执行：

```powershell
mysql -uroot -pmysql < backend/scripts/init_db.sql
```

## 后端启动

```powershell
cd E:\sysml\sysml-docgen-system\backend
pip install -r requirements.txt
python run.py
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 前端启动

```powershell
cd E:\sysml\sysml-docgen-system\frontend
npm install
npm run dev
```

访问：

```text
http://127.0.0.1:5173
```

## 推荐演示流程

1. 注册一个 `admin` 用户。
2. 创建项目。
3. 进入模型管理，上传 `docs/sample-sysml-model.json`。
4. 查看解析出的模型元素和关系。
5. 进入模板管理，创建默认模板。
6. 进入文档生成，选择项目、模型、模板并生成文档。
7. 预览文档并导出 HTML/DOCX/PDF。
