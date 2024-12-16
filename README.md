## OBGym Core

<p align="center">
<a href="https://github.com/jungheil/OBGym_core"><img src="https://img.shields.io/badge/OBGym-green.svg" title="OBGym"></a>
<a href="https://github.com/jungheil"><img src="https://img.shields.io/badge/Author-jungheil-green.svg" title="Author"></a>
<a href="./LICENSE"><img src="https://img.shields.io/github/license/jungheil/OBGym_core?color=yellow" title="LICENSE"></a>
<a href="https://www.python.org/"><img src="https://img.shields.io/github/languages/top/jungheil/OBGym_core" title="Language"></a>
<a href="https://github.com/jungheil/OBGym_core/actions/workflows/create_publish_image.yml"><img src="https://img.shields.io/github/v/tag/jungheil/OBGym_core?label=version" title="Version"></a>
<a href="https://github.com/jungheil/OBGym_core/actions/workflows/create_publish_image.yml"><img src ='https://img.shields.io/github/actions/workflow/status/jungheil/OBGym_core/create_publish_image.yml?label=Build' title="Build"></a>
</p>


OBGym Core 是一个用于大山中学体育场馆预约的自动化工具。它提供了一个简单的接口来管理账户、查询场地信息以及预约场地。

在使用本项目前，请务必仔细阅读[声明](#声明)部分。如果您觉得本项目对您有帮助，欢迎点亮 star ⭐，这是对我最大的支持与鼓励。

![OBGym](./assets/obgym.gif)

### 项目背景

近年来，随着社会经济的迅猛发展和居民生活水平的显著提升，公众对于体育运动及健康生活方式的关注度持续攀升。特别是在学校中，学生群体对于体育锻炼的需求呈现出明显的增长态势。然而，体育经费的有限性与日益膨胀的运动需求之间的矛盾盾日益突出。例如，学生每年体育经费为500元，而羽毛球场地每小时的费用为30元，这导致一年经费甚至不足以支持半年内每周一次的羽毛球活动。在缺少体育经费的背景下，学生采取了多种方式进行体育锻炼，包括蹭他人场地、在场地无人时使用、蹭体育课以及请求他人代为预约等。本项目受到网络购物中的锁定库行为的启发，开发了一种预约场地的方法。

### 项目概述

OBGym 项目由两个主要组件构成:

- [OBGym Core](https://github.com/jungheil/OBGym_core): 作为项目的核心引擎，实现所有基础功能，并提供了完整的 API 接口供调用
- [OBGym App](https://github.com/jungheil/OBGym_app): 基于 OBGym Core 开发的 Web 应用程序，提供了直观友好的用户界面，由 AI 开发

本项目采用 Docker 容器化部署方案，极大简化了部署流程。用户只需在后台启动容器服务，即可通过 Web 界面进行场地预约操作。系统会自动在后台处理并执行用户的所有预约指令。

### 部署指南

1. 安装并启动 Docker 环境

   访问 [Docker 官方网站](https://www.docker.com/) 下载并安装 Docker Desktop。

   注意：下载过程可能需要使用代理服务。安装完成后，启动 Docker Desktop 应用程序。

2. 获取配置文件

   从项目仓库下载 `docker-compose.yml` 配置文件：[下载地址](https://raw.githubusercontent.com/jungheil/OBGym_core/refs/heads/main/docker-compose.yml)

   注意：下载过程可能需要使用代理服务。

3. 准备运行环境

   使用快捷键 `Win+R` 打开运行窗口，输入 `wt` 并回车以启动终端。

   在终端中导航至已下载的 `docker-compose.yml` 文件所在目录。

4. 获取 Docker 镜像

   在终端中执行以下命令拉取所需的 Docker 镜像：

   ``` bash
   docker compose pull
   ```

5. 启动服务

   执行以下命令启动 OBGym 服务：

   ``` bash
   docker compose up
   ```

### 使用指南

<video src="https://github.com/user-attachments/assets/d10c671f-46f9-40ed-91a6-2307f819eeb1" controls="controls" muted="muted" style="max-height:720px; min-height: 200px"></video>

1. 打开浏览器，访问系统地址 `http://127.0.0.1:16080`

2. 使用管理员账号登录系统
   
   - 账号：`admin`
   - 密码：`admin`

3. 添加您的个人账户信息
   
   - 使用中央身份验证系统的账号密码
   - 支持添加多个账户

4. 预约场地
   
   - 选择目标校区和场馆
   - 选择具体场地和时间段
   - 确认预约信息无误

5. 提交预约任务
   
   - 系统将在后台自动执行预约
   - 可在任务列表中查看预约进度

### 常见问题

1. 账号密码的安全性说明
   
   本项目承诺不会以任何方式窃取您的账户信息，账号密码将加密存储在您的本地设备中，为确保账号安全，请注意以下事项：

   - 请勿在他人部署的项目中添加您的账号信息
   - 由于密码通过 HTTP 明文传输，远程访问 Web 界面时存在被中间人攻击的风险
   - 请仅在可信任的个人设备上部署使用，若本地数据库被恶意获取，虽然密码非明文存储，但密码仍会泄露

2. 为什么不使用 Cookies 登录方式？
   
   由于 Cookies 的有效期较短，需要频繁重新登录。

3. “仅预约”功能是什么?
   
   “仅预约”是指系统只进行场地预约而不自动支付。系统会在后台每隔30分钟自动尝试预约，直到所选场地的使用时间结束。这样可以让用户有更多时间决定是否付费使用该场地。故请勿在所选场地的使用时间结束前关闭程序。

4. 登录失败的常见原因
   
   - 不在校内网络环境
   - 请确保输入的账号密码正确
   - AI 验证码识别出现错误

5. 如何修改 Web 界面访问密码？
   
   如需修改访问密码，请编辑 `docker-compose.yml` 文件，找到并修改以下环境变量：
   - `AUTH_USER`: 登录用户名
   - `AUTH_PASS`: 登录密码

6. 遇到未知错误如何处理？
   
   如果遇到系统异常或未知错误，请按以下步骤处理：

   - 保存完整的系统运行日志
   - 记录故障发生的具体时间
   - 详细描述故障现象和操作步骤
   - 在项目 GitHub 页面提交 issue，附上以上信息

### API 文档

本系统提供了完整的 API 接口,详细的接口定义和使用说明请参考 `obgym_api.py` 文件。以下将介绍主要的 API 功能和数据结构。

#### 数据模型

- `GymCampus`: 校区信息
  - name: 校区名称
  - code: 校区唯一标识码

- `GymFacility`: 场馆设施信息
  - name: 设施名称
  - serviceid: 设施服务ID

- `GymArea`: 场地信息
  - sname: 场地名称
  - sdate: 预约日期
  - timeno: 时间段编号
  - serviceid: 设施服务ID
  - areaid: 场地ID
  - stockid: 库存ID

- `GymOrder`: 预约订单信息
  - orderid: 订单ID
  - createdate: 创建日期

- `Job`: 任务信息
  - status: 任务状态(PENDING/RUNNING/RETRY/SUCCESS/FAILED)
  - job_level: 任务级别(MAIN/USER)
  - job_id: 任务ID
  - description: 任务描述
  - job_type: 任务类型(UNKNOW/RENEW/BOOK/BOOK_AND_PAY)
  - result: 任务结果列表
  - failed_count: 失败次数
  - created_at: 创建时间
  - updated_at: 更新时间
  - task_todo: 待执行任务信息(可选)

#### 账户管理

- `add_account(account: str, password: str) -> Dict`
  - 功能：添加新账户
  - 输入：
    - account: 账户用户名
    - password: 账户密码
  - 返回：包含操作结果的字典

- `remove_account(account: str) -> Dict`
  - 功能：删除账户
  - 输入：
    - account: 要删除的账户用户名
  - 返回：包含操作结果的字典

- `get_accounts() -> List[Dict]`
  - 功能：获取所有账户列表
  - 输入：无
  - 返回：账户信息列表

- `renew_account(account: str) -> Dict`
  - 功能：更新账户登录状态
  - 输入：
    - account: 账户用户名
  - 返回：包含操作结果的字典

#### 场馆查询

- `get_campus(account: str) -> List[GymCampus]`
  - 功能：获取校区列表
  - 输入：
    - account: 账户用户名
  - 返回：GymCampus对象列表

- `get_facility(campus: GymCampus, account: str) -> List[GymFacility]`
  - 功能：获取场馆设施列表
  - 输入：
    - campus: 校区对象
    - account: 账户用户名
  - 返回：GymFacility对象列表

- `get_area(facility: GymFacility, date: str, account: str) -> List[GymArea]`
  - 功能：获取场地信息
  - 输入：
    - facility: 场馆设施对象
    - date: 日期字符串
    - account: 账户用户名
  - 返回：GymArea对象列表

#### 任务管理

- `only_book(area: GymArea, account: str) -> Dict`
  - 功能：创建预约任务
  - 输入：
    - area: 场地对象
    - account: 账户用户名
  - 返回：包含job_id的字典

- `book_and_pay(area: GymArea, account: str) -> Dict`
  - 功能：创建预约并支付任务
  - 输入：
    - area: 场地对象
    - account: 账户用户名
  - 返回：包含job_id的字典

- `get_all_jobs() -> Dict`
  - 功能：获取所有任务列表
  - 输入：无
  - 返回：包含任务列表的字典

- `get_job_info(job_id: str) -> Job`
  - 功能：获取任务详细信息
  - 输入：
    - job_id: 任务ID
  - 返回：Job对象，包含任务的详细信息

- `remove_job(job_id: str) -> Dict`
  - 功能：删除任务
  - 输入：
    - job_id: 要删除的任务ID
  - 返回：包含操作结果的字典

### 许可证

本项目采用木兰宽松许可证第2版（Mulan PSL v2）进行许可。

### 贡献

欢迎提交 Issue 和 Pull Request！

### 声明

本项目按“现状”提供，仅供技术学习和交流使用，不提供任何明示或暗示的保证。在任何情况下，作者或版权所有者不对任何索赔、损害或其他责任负责。本项目使用本项目所产生的任何违规行为与作者无关。

如有任何问题或侵权行为，请及时与作者联系，我将立即删除相关内容。

使用本项目即表示您已完全理解并同意:

1. 本项目仅用于学习和研究目的
2. 不得将本项目用于任何违法或不当用途
3. 使用本项目所造成的任何后果由使用者自行承担
