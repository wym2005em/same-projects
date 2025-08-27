# same-projects
same-projects

# 项目数据库展示工具

一个基于FastAPI和MySQL的项目数据管理与展示平台，提供项目列表查询、详情查看、分数更新、分类统计等功能，并配套前端页面实现交互操作。

## 功能特点

- 项目数据分页查询，支持分类筛选、关键词搜索和排序
- 项目详情查看与分数更新
- 项目分类（一级/二级）管理与统计分析
- 支持项目可见性（私有/公开）筛选
- 前端页面与后端API分离，通过RESTful接口交互
- 跨域请求支持，便于前端开发调试

## 技术栈

- 后端：FastAPI、Python 3.8+、MySQL
- 前端：HTML、JavaScript、Bootstrap 5、jQuery
- 数据库：MySQL 8.0+

## 安装与配置

### 前提条件

- Python 3.8 及以上版本
- MySQL 数据库环境

### 安装步骤

1. 克隆仓库或下载项目代码
   ```bash
   git clone https://github.com/wym2005em/same-projects.git
   cd same-peojects

# 安装依赖包
pip install -r requirements.txt

# 开发环境运行
python main.py