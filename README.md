# OBGym Core

OBGym Core 是一个用于大山中学体育场馆预约的自动化工具。它提供了一个简单的接口来管理账户、查询场地信息以及预约场地。

## API 文档

## 数据模型

- `GymCampus`: 校区信息
- `GymFacility`: 场馆设施信息
- `GymArea`: 场地信息
- `GymOrder`: 预约订单信息
- `Job`: 任务信息

### 账户管理

- `add_account(account: str, password: str)`: 添加新账户
- `remove_account(account: str)`: 删除账户
- `get_accounts()`: 获取所有账户列表
- `renew_account(account: str)`: 更新账户登录状态

### 场馆查询

- `get_campus(account: str)`: 获取校区列表
- `get_facility(campus: GymCampus, account: str)`: 获取场馆设施列表
- `get_area(facility: GymFacility, date: str, account: str)`: 获取场地信息

### 任务管理

- `only_book(area: GymArea, account: str)`: 创建预约任务
- `get_all_jobs()`: 获取所有任务列表
- `get_job_info(job_id: str)`: 获取任务详细信息
- `remove_job(job_id: str)`: 删除任务

## 许可证

本项目采用木兰宽松许可证第2版（Mulan PSL v2）进行许可。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 免责声明

本软件按"现状"提供，不提供任何明示或暗示的保证。在任何情况下，作者或版权所有者不对任何索赔、损害或其他责任负责。
