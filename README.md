# MediaManager

一个类 [tinyMediaManager](https://www.tinymediamanager.org/) 的**自研媒体管理器**,专为 NAS 设计,通过 Docker 一键部署。

与 tinyMediaManager 官方镜像(在容器内跑桌面 GUI + VNC)不同,本项目是一个**原生 Web 应用**(FastAPI + Vue3),浏览器直接访问,体验更流畅,资源占用更低。

## ✨ 功能

- 📁 **媒体库扫描** — 扫描目录,用 `guessit` 自动解析文件名(标题/年份/季/集/分辨率)
- 🔍 **元数据刮削** — 接入 TMDB,自动匹配电影/剧集,获取海报、剧情简介、评分、演员
- 🖼️ **NFO & 图片管理** — 生成 Kodi/Jellyfin/Emby 兼容的 `.nfo`,下载海报/背景图到媒体目录;支持回读已有 NFO 恢复元数据
- 🏷️ **重命名与整理** — 可配置命名模板,预览 → 勾选 → 执行,支持**撤销**;冲突高亮
- 🎬 **电影 + 电视剧** — 完整支持剧集的季/集结构

## 🏗️ 架构

```
media-manager/
├── docker-compose.yml      # 2 服务: backend + frontend(SQLite 无需独立数据库)
├── .env.example
├── backend/                # FastAPI + SQLModel + SQLite(WAL)
│   └── app/
│       ├── models/         # library / movie / tvshow / season / episode / task / rename_log
│       ├── services/       # scanner / tmdb / scraper / nfo / renamer / images / tasks
│       ├── core/           # naming(命名模板 token 引擎)
│       ├── routers/        # REST API
│       └── main.py
└── frontend/               # Vue3 + Vite + Pinia + Element Plus
    └── src/
        ├── api/            # 类型化 API 客户端
        ├── components/     # ScrapeDialog(刮削匹配弹窗)
        └── views/          # Dashboard / Libraries / MovieList/Detail / TvList/Detail / RenamePreview / Settings
```

## 🚀 部署到 NAS

整体思路:NAS 上装好 Docker,把本项目文件夹传上去,编辑 `.env` 填入媒体目录和 TMDB Key,`docker compose up -d` 启动,浏览器访问即可。

### 前置条件
- NAS 已安装 **Docker**(群晖/威联通用「套件中心」装 Container Manager / Container Station;通用 Linux 装 Docker Engine + Compose 插件)
- 拥有 **SSH 访问** 或 文件管理权限(用于上传项目文件 + 编辑 `.env`)
- 一个有读写权限的**媒体目录**(如 `/volume1/video`)

### 第 0 步:准备 TMDB API Key(免费,强烈建议)
本项目用 TMDB 获取海报/简介/评分。没有 Key 也能用(仅文件名解析 + 重命名),但海报/元数据会是空的。

1. 访问 https://www.themoviedb.org/settings/api → 注册账号
2. 选择 **Developer** 类型(免费,填几个理由即可)
3. 拿到 **API Key (v3 auth)**,记下来

### 第 1 步:把项目文件放到 NAS

把整个 `media-manager` 文件夹上传到 NAS。**两种方式任选:**

**方式 A — SSH 命令行(推荐,群晖/威联通通用):**
```bash
# 在本机(Mac)打包,排除掉不需要的大目录
cd /Users/xiong/ZCodeProject
tar --exclude='media-manager/media' \
    --exclude='media-manager/backend/.venv' \
    --exclude='media-manager/frontend/node_modules' \
    --exclude='media-manager/frontend/dist' \
    -czf mm.tar.gz media-manager

# 传到 NAS(把 xiong@NAS_IP 换成你的 NAS 账号和 IP)
scp mm.tar.gz xiong@NAS_IP:/volume1/docker/

# SSH 进 NAS 并解压
ssh xiong@NAS_IP
cd /volume1/docker && tar -xzf mm.tar.gz && cd media-manager
```

**方式 B — 图形化(不会命令行):**
- 群晖:用 File Station 在 `/volume1/docker/` 下新建 `media-manager` 文件夹,把电脑上的项目文件(除了 `media/`、`node_modules/`、`.venv/`)全部拖进去
- 威联通:用 File Station 放到 `/share/Container/` 下

> 解压/上传后,确认目录里有 `docker-compose.yml`、`backend/`、`frontend/`、`.env.example`。

### 第 2 步:查 UID/GID(避免文件权限问题)

NAS 上媒体目录通常不属于 root。容器要读写这些文件,必须用对应的 uid/gid 运行。**SSH 进 NAS 执行:**
```bash
# 看你的账号的 uid / gid(下面用到的那个 xiong 换成你的 NAS 用户名)
id
# 输出示例: uid=1026(xiong) gid=100(users) ...
# 所以 PUID=1026, PGID=100
```
> 群晖默认普通用户 gid 通常是 `100`(users 组)。

### 第 3 步:配置 `.env`

在项目目录下复制配置模板并编辑:
```bash
cp .env.example .env
nano .env        # 或 vi .env
```
按实际情况填写(**关键 4 项**):
```ini
TMDB_API_KEY=第0步拿到的key          # 没有就留空,功能受限但不影响扫描/重命名
MEDIA_DIR=/volume1/video             # ← 改成你 NAS 上媒体目录的真实绝对路径(读写)
PUID=1026                            # ← 第2步查到的 uid
PGID=100                             # ← 第2步查到的 gid
FRONTEND_PORT=8080                   # 对外访问端口(80 被占用就换 8080/3000)
```
其他项默认即可(`BACKEND_PORT`、`BUILD_TARGET=prod`、`CORS_ORIGINS=*`)。

### 第 4 步:启动

```bash
docker compose up -d --build
```
首次会构建镜像(下载 Python/Node/nginx 基础镜像 + 装依赖,**5~15 分钟**,取决于 NAS 性能和网速)。构建完会看到 `Started`。

查看状态 / 日志:
```bash
docker compose ps              # 看两个服务是不是 Up
docker compose logs -f backend # 看后端日志(排查问题用)
```

浏览器访问 **`http://NAS_IP:8080`**(端口用你在 `.env` 里设的 `FRONTEND_PORT`)。

> 不想用命令行构建?群晖可打开 **Container Manager → 项目 → 新增**,项目目录选 `media-manager`,它自动识别 `docker-compose.yml`,点创建即可。威联通同理在 **Container Station → 应用程序 → 创建**。

### 第 5 步:首次使用
1. **媒体库** → 新建 → 填名称、类型(电影/电视剧)、**媒体根目录下的子路径**(如媒体目录是 `/volume1/video`,里面放电影的子文件夹叫 `Movies`,就填 `Movies`)
2. 点「扫描」→ 自动解析所有文件名
3. 若填了 TMDB Key 且开启「自动刮削」,会自动匹配海报/简介;也可在电影详情页手动搜索纠错
4. **重命名** 页:选媒体库 → 资源列表自动出现 → 勾选 → 执行(可撤销)

### 常见问题

| 现象 | 原因 / 解决 |
|------|------------|
| 扫描后媒体目录文件属主是 root | `PUID/PGID` 没设对,用 `id` 重新查后改 `.env`,再 `docker compose up -d` |
| 海报/简介全是空 | 没填 `TMDB_API_KEY`,或 Key 无效 |
| 容器内读不到媒体文件 | `MEDIA_DIR` 路径不对,或该目录容器没读写权限 |
| `80` 端口被占用 | `.env` 改 `FRONTEND_PORT=8080`(或任意空闲端口) |
| 构建很慢/失败 | NAS 网络拉镜像慢,可配置国内镜像加速;或本机构建好推到 NAS |
| 想更新到新版本 | 重新上传项目文件覆盖,然后 `docker compose up -d --build` |

### 反向代理 / HTTPS(可选)
若想用域名或 HTTPS 访问,在 NAS 的反向代理(群晖:控制面板 → 登录门户 → 高级 → 反向代理)里把外部端口转发到 `localhost:8080` 即可。`nginx.conf` 已关闭 `proxy_buffering`,SSE 任务进度不会受影响。

### 升级 / 备份
- **数据库**:在 `mm_data` 这个 Docker 卷里(`/data/media_manager.db`),用 `docker compose down` 不会丢;想彻底备份就备份这个卷或执行 `docker run --rm -v mm_data:/d -v $PWD:/o alpine tar czf /o/mm_db_backup.tgz -C /d .`
- **媒体文件**:就在你挂载的 `MEDIA_DIR`,容器重建不影响它们
- **升级**:`git pull`(或重新上传)→ `docker compose up -d --build`

---

## 🌐 在线发布 + NAS 直接拉取(推荐:NAS 零编译)

上面的方式要在 NAS 上编译镜像,NAS 的弱 CPU 可能要 10~20 分钟。**更好的办法:源码推到 GitHub,用 GitHub Actions 自动构建镜像到 GHCR(公开),NAS 上直接 `docker pull` 即用,几秒启动。**

### 第一步:源码推到 GitHub(在你的 Mac 上做一次)

```bash
cd /Users/xiong/ZCodeProject/media-manager

# 初始化 + 提交(测试媒体/.venv/node_modules/.env 已被 .gitignore 排除)
git init
git add .
git commit -m "init: MediaManager"

# 在 GitHub 网页上新建一个「公开」空仓库,比如 your-username/media-manager
# (不要勾选 README/.gitignore,空仓库即可)
git branch -M main
git remote add origin https://github.com/<your-username>/media-manager.git
git push -u origin main
```

### 第二步:确认 Actions 自动构建

项目自带 `.github/workflows/docker-publish.yml`。推送后:
1. 打开仓库的 **Actions** 标签页
2. 会看到「Build & Publish Docker Images」正在跑(首次约 8~15 分钟,构建 amd64 + arm64 双架构)
3. **无需配置任何 secret**——`GITHUB_TOKEN` 是 GitHub 自动提供的
4. 构建成功后,镜像出现在你头像 → **Packages**(或 `github.com/<your-username>?tab=packages`),公开镜像任何人都能拉

构建产物(把 `<your-username>` 换成你的 GitHub 用户名,**全小写**):
- `ghcr.io/<your-username>/media-manager-backend:latest`
- `ghcr.io/<your-username>/media-manager-frontend:latest`

之后每次 `git push` 到 `main`,只要改动了 `backend/` 或 `frontend/`,就会自动重新构建发布。

### 第三步:NAS 上拉取部署(NAS 零编译)

NAS 上**只需要 2 个文件**:本仓库的 `docker-compose.nas.yml` 和 `.env.example`。

```bash
# 1) SSH 进 NAS,建个目录
mkdir -p /volume1/docker/media-manager && cd /volume1/docker/media-manager

# 2) 下载这两个文件(或者用 File Station 上传)
#    把 <your-username> 换成你的 GitHub 用户名
curl -O https://raw.githubusercontent.com/<your-username>/media-manager/main/docker-compose.nas.yml
curl -O https://raw.githubusercontent.com/<your-username>/media-manager/main/.env.example

# 3) 编辑 compose 文件,把镜像名里的 <your-username> 换成你的(全小写)
nano docker-compose.nas.yml

# 4) 配置环境
cp .env.example .env && nano .env
#    必填:TMDB_API_KEY / MEDIA_DIR / PUID / PGID / FRONTEND_PORT

# 5) 启动(只拉镜像,不编译,几秒到一分钟)
docker compose -f docker-compose.nas.yml up -d

# 6) 访问 http://NAS_IP:8080
```

**升级到新版本:** 源码更新后 Actions 会自动重建镜像,NAS 上只需:
```bash
cd /volume1/docker/media-manager
docker compose -f docker-compose.nas.yml pull      # 拉最新镜像
docker compose -f docker-compose.nas.yml up -d     # 重建容器(数据不丢)
```

> **公开仓库的好处:** NAS 上 `docker pull` 公开镜像**无需登录**,也不用配任何 token。私有仓库则需要先 `docker login ghcr.io`。
>
> **双架构镜像:** Actions 同时构建 `linux/amd64`(Intel NAS)和 `linux/arm64`(如 N100/树莓派/部分新 NAS),NAS 会自动拉到匹配的架构。

## ⚙️ 关键设计

- **SQLite + WAL**: 单容器,无独立数据库,WAL 模式保证扫描/刮削并发读不阻塞
- **PUID/PGID**: 容器启动后用 `gosu` 切到指定 uid/gid,避免 NAS 挂载目录产生 root 属主文件(群晖/威联通常见坑)
- **命名模板 token**: `{title}` `{year}` `{tmdbid}` `{resolution}` `{ext}`(剧集额外支持 `{season}` `{episode}` `{sXXeYY}`)
- **重命名安全**: 默认只预览,冲突项(目标已存在)禁选,每次执行记 `RenameLog`,可按批次撤销
- **NFO 兼容**: 输出格式对齐 Kodi/Jellyfin/Emby,可直接被这些媒体中心读取

## 🔧 本地开发

```bash
# 后端(需 Python 3.12+)
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端(另开终端)
cd frontend && npm install && npm run dev
# 访问 http://localhost:5173(自动代理 /api 到 8000)
```

## 📋 默认命名模板

| 类型 | 默认模板 | 示例结果 |
|------|---------|---------|
| 电影 | `{title} ({year})/{title} ({year}){ext}` | `Inception (2010)/Inception (2010).mkv` |
| 剧集 | 可改为 `{title}/Season {season}/{title} S{sXXeYY}{ext}` | `Breaking Bad/Season 01/Breaking Bad S01E05.mkv` |

## 🗂️ API 文档
启动后端后访问 `http://NAS_IP:8000/docs` 查看自动生成的 OpenAPI 文档。

## 依赖技术栈
- 后端:FastAPI · SQLModel · httpx · guessit · SQLite
- 前端:Vue 3 · Vite · Pinia · Element Plus · TypeScript
- 数据源:[TMDB](https://www.themoviedb.org/)

---

> 本项目不分发、不抓取任何受版权保护的媒体内容,仅做本地文件名解析与开源元数据(TMDB)整理,与 tinyMediaManager 无官方关联。
