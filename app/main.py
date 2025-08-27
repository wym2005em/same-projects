from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import mysql.connector
from mysql.connector import Error
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from starlette.responses import RedirectResponse
app = FastAPI(title="项目数据库展示工具")
# 挂载静态文件目录（前端页面存放目录）
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 数据库连接配置（请根据实际环境修改）
DB_CONFIG = {
    'host': 'same-data-mysql.c5ickguoyn7s.us-west-1.rds.amazonaws.com',
    'user': 'admin',
    'password': '!1qazxcvB',  # 生产环境建议使用环境变量存储
    'database': 'data',
    'port': 3306,
    'charset': 'utf8mb4',
    'autocommit': False
}
# 数据模型定义
class Project(BaseModel):
    project_id: str
    manual_title: str
    manual_summary: str
    author_id: str
    main_domain: Optional[str]
    create_tm: Optional[str]
    project_forked_acc_cnt: int
    project_opened_acc_cnt: int
    author_name: Optional[str] = None
    category_l1: Optional[str]
    category_l2: Optional[str]
    manual_score: float
    manual_score_updated: float  # 更新后分数字段
    screenshot_url: Optional[str]
    description: Optional[str]  # 补充搜索用字段
    project_visibility: str  # 新增：可见性状态
class PaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    projects: List[Project]
class CategoriesResponse(BaseModel):
    l1: List[str]
    l2Map: Dict[str, List[str]]
class UpdateScoreRequest(BaseModel):
    new_score: float
def get_db_connection():
    """创建数据库连接"""
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"数据库连接错误: {e}")
    return connection
@app.get("/api/categories", response_model=CategoriesResponse)
def get_categories():
    """获取所有分类数据"""
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # 获取所有一级分类
        cursor.execute("""
            SELECT DISTINCT category_l1 
            FROM projects_8
            WHERE category_l1 IS NOT NULL AND category_l1 != '' 
            ORDER BY category_l1
        """)
        l1_categories = [row['category_l1'] for row in cursor.fetchall()]
        
        # 构建一级分类到二级分类的映射
        l2_map = {}
        for l1 in l1_categories:
            cursor.execute("""
                SELECT DISTINCT category_l2 
                FROM projects_8
                WHERE category_l1 = %s 
                  AND category_l2 IS NOT NULL 
                  AND category_l2 != '' 
                ORDER BY category_l2
            """, (l1,))
            l2_categories = [row['category_l2'] for row in cursor.fetchall()]
            l2_map[l1] = l2_categories
            
        return {'l1': l1_categories, 'l2Map': l2_map}
        
    except Error as e:
        raise HTTPException(status_code=500, detail=f"数据库查询错误: {str(e)}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
@app.get("/api/projects", response_model=PaginatedResponse)
def get_projects(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(8, ge=1, le=100, description="每页项目数"),
    sort_by: str = Query("manual_score_updated", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc或desc"),
    category_l1: Optional[str] = Query(None, description="一级分类筛选"),
    category_l2: Optional[str] = Query(None, description="二级分类筛选"),
    search: Optional[str] = Query(None, description="搜索关键词，匹配description和manual_summary"),
    project_visibility: Optional[str] = Query(None, description="可见性筛选: private或public")  # 新增：可见性筛选参数
):
    """获取分页的项目列表，支持排序、分类筛选和搜索"""
    # 验证排序参数
    valid_sort_fields = ["manual_score", "manual_score_updated", "create_tm", "project_opened_acc_cnt"]
    if sort_by not in valid_sort_fields:
        sort_by = "manual_score_updated"
        
    sort_order = sort_order.lower() if sort_order.lower() in ["asc", "desc"] else "desc"
    
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    try:
        cursor = connection.cursor(dictionary=True)
        offset = (page - 1) * limit
        
        # 构建查询条件
        where_clause = []
        params = []
        
        if category_l1:
            where_clause.append("category_l1 = %s")
            params.append(category_l1)
        
        if category_l2:
            where_clause.append("category_l2 = %s")
            params.append(category_l2)
        
        if search:
            where_clause.append("(description LIKE %s OR manual_summary LIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        # 新增：可见性筛选条件
        if project_visibility in ["private", "public"]:
            where_clause.append("project_visibility = %s")
            params.append(project_visibility)
        
        # 构建查询语句
        query = f"""
        SELECT project_id, manual_title, manual_summary, author_id, main_domain, 
               DATE_FORMAT(create_tm, '%Y-%m-%d %H:%i') as create_tm,
               project_forked_acc_cnt, project_opened_acc_cnt, author_name,
               category_l1, category_l2, manual_score, manual_score_updated, 
               screenshot_url, description, project_visibility  # 新增：查询可见性字段
        FROM projects_8
        """
        
        if where_clause:
            query += " WHERE " + " AND ".join(where_clause)
            
        query += f" ORDER BY {sort_by} {sort_order} LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, tuple(params))
        projects = cursor.fetchall()
        
        # 查询总记录数
        count_query = "SELECT COUNT(*) as total FROM projects_8"
        if where_clause:
            count_query += " WHERE " + " AND ".join(where_clause)
        
        cursor.execute(count_query, tuple(params[:-2]))  # 排除limit和offset
        total = cursor.fetchone()['total']
        
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "projects": projects
        }
        
    except Error as e:
        raise HTTPException(status_code=500, detail=f"数据库查询错误: {str(e)}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
@app.get("/api/projects/{project_id}")
def get_project_detail(project_id: str):
    """获取项目详情（返回所有字段）"""
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT * FROM projects_8 WHERE project_id = %s"
        cursor.execute(query, (project_id,))
        project = cursor.fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
            
        return project
        
    except Error as e:
        raise HTTPException(status_code=500, detail=f"数据库查询错误: {str(e)}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
@app.put("/api/projects/{project_id}/score")
def update_project_score(project_id: str, request: UpdateScoreRequest):
    """更新项目的manual_score_updated字段"""
    if not (0 <= request.new_score <= 1000):
        raise HTTPException(status_code=400, detail="分数必须在0到1000之间")
    
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    try:
        cursor = connection.cursor()
        
        query = """
        UPDATE projects_8 
        SET manual_score_updated = %s 
        WHERE project_id = %s
        """
        cursor.execute(query, (request.new_score, project_id))
        connection.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="项目不存在")
            
        return {"status": "success", "message": "分数已更新", "new_score": request.new_score}
        
    except Error as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"数据库更新错误: {str(e)}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# 新增：项目分析API
@app.get("/api/analysis")
def get_project_analysis():
    """获取项目分类统计分析数据"""
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # 查询一级分类统计
        cursor.execute("""
            SELECT category_l1,
                   COUNT(DISTINCT project_id) as project_count,
                   COUNT(DISTINCT author_id) as author_count
            FROM projects_8
            WHERE category_l1 IS NOT NULL AND category_l1 != ''
            GROUP BY category_l1
            ORDER BY project_count DESC
        """)
        l1_analysis = cursor.fetchall()
        
        # 查询二级分类统计
        cursor.execute("""
            SELECT category_l1,
                   category_l2,
                   COUNT(DISTINCT project_id) as project_count,
                   COUNT(DISTINCT author_id) as author_count
            FROM projects_8
            WHERE category_l1 IS NOT NULL AND category_l1 != ''
              AND category_l2 IS NOT NULL AND category_l2 != ''
            GROUP BY category_l1, category_l2
            ORDER BY category_l1, project_count DESC
        """)
        l2_analysis = cursor.fetchall()
        
        # 构建二级分类映射
        l2_map = {}
        for item in l2_analysis:
            l1 = item['category_l1']
            if l1 not in l2_map:
                l2_map[l1] = []
            l2_map[l1].append({
                'category_l2': item['category_l2'],
                'project_count': item['project_count'],
                'author_count': item['author_count']
            })
        
        return {
            'l1_analysis': l1_analysis,
            'l2_map': l2_map
        }
        
    except Error as e:
        raise HTTPException(status_code=500, detail=f"数据库查询错误: {str(e)}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# 根路由重定向到前端页面
@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8070)  # 开发环境启用热重载