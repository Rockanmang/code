from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.models.user import User
from app.models.research_group import ResearchGroup, UserResearchGroup
from app.models.literature import Literature
from app.auth import verify_password  # 导入auth.py中的验证函数
from app.utils.auth_helper import require_group_membership, verify_group_membership
from app.utils.file_handler import validate_upload_file, generate_file_path, save_uploaded_file, get_file_info
from app.utils.text_extractor import extract_metadata_from_file
from app.utils.error_handler import (
    log_error, log_success, handle_file_upload_error, handle_permission_error,
    validate_file_upload, safe_file_operation, FileUploadError, PermissionError, ValidationError
)
from app.schemas import FileUploadResponse, LiteratureListResponse, LiteratureListItem
from jose import jwt
from datetime import datetime, timedelta
import logging
from fastapi.responses import FileResponse
from app.utils.auth_helper import verify_literature_access, get_literature_with_permission, verify_file_exists, get_content_type

# 配置日志
logger = logging.getLogger(__name__)

app = FastAPI(title="文献管理系统", description="AI驱动的协作文献管理平台", version="1.0.0")

# JWT 配置
SECRET_KEY = "your-secret-key"  # 替换为随机字符串，例如 "mysecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

@app.get("/")
def read_root():
    """根路径 - 返回API基本信息"""
    return {
        "message": "欢迎使用文献管理系统API",
        "version": "1.0.0",
        "status": "运行中",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

def get_current_user(db: Session = Depends(get_db), token: str = Depends(OAuth2PasswordBearer(tokenUrl="login"))):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的令牌")
    except Exception:
        raise HTTPException(status_code=401, detail="无效的令牌")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    logger.info(f"用户登录尝试: {form_data.username}")
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        log_error("user_login", Exception("登录失败"), extra_info={"username": form_data.username})
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    
    log_success("user_login", user.id, {"username": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/groups/create")
def create_group(name: str, institution: str, description: str, research_area: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # 只传4个参数，模型内部自己生成 invitation_code
        group = ResearchGroup(
            name=name,
            institution=institution,
            description=description,
            research_area=research_area,
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        membership = UserResearchGroup(user_id=current_user.id, group_id=group.id)
        db.add(membership)
        db.commit()
        
        log_success("group_create", current_user.id, {
            "group_id": group.id,
            "group_name": name,
            "institution": institution
        })
        
        return {"group_id": group.id, "invitation_code": group.invitation_code}
        
    except Exception as e:
        log_error("group_create", e, current_user.id, {"group_name": name})
        raise HTTPException(status_code=500, detail="创建研究组失败")

@app.post("/groups/join")
def join_group(group_id: str, invitation_code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        group = db.query(ResearchGroup).filter(ResearchGroup.id == group_id).first()
        if not group or group.invitation_code != invitation_code:
            log_error("group_join", Exception("无效的课题组ID或邀请码"), current_user.id, {
                "group_id": group_id,
                "provided_code": invitation_code
            })
            raise HTTPException(status_code=400, detail="无效的课题组ID或邀请码")
        
        existing = db.query(UserResearchGroup).filter(
            UserResearchGroup.user_id == current_user.id,
            UserResearchGroup.group_id == group_id
        ).first()
        if existing:
            log_error("group_join", Exception("用户已加入该课题组"), current_user.id, {"group_id": group_id})
            raise HTTPException(status_code=400, detail="用户已加入该课题组")
        
        membership = UserResearchGroup(user_id=current_user.id, group_id=group_id)
        db.add(membership)
        db.commit()
        
        log_success("group_join", current_user.id, {
            "group_id": group_id,
            "group_name": group.name
        })
        
        return {"message": "成功加入课题组"}
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("group_join", e, current_user.id, {"group_id": group_id})
        raise HTTPException(status_code=500, detail="加入研究组失败")

# ===== 文献管理接口 =====

@app.post("/literature/upload", response_model=FileUploadResponse)
async def upload_literature(
    file: UploadFile = File(...),
    group_id: str = Form(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传文献到指定研究组 - 增强版错误处理
    """
    operation_info = {
        "filename": file.filename,
        "group_id": group_id,
        "file_size": None
    }
    
    try:
        # 1. 基础验证
        validate_file_upload(file, group_id, current_user.id)
        
        # 2. 验证用户是否为指定研究组成员
        try:
            require_group_membership(current_user.id, group_id, db)
        except HTTPException as e:
            raise PermissionError(e.detail)
        
        # 3. 验证文件
        is_valid, error_msg = validate_upload_file(file)
        if not is_valid:
            raise ValidationError(error_msg)
        
        # 4. 获取文件信息
        file_info = get_file_info(file)
        operation_info["file_size"] = file_info["file_size"]
        
        # 5. 生成存储路径
        full_path, relative_path = generate_file_path(group_id, file.filename)
        
        # 6. 安全保存文件到磁盘
        def save_file():
            return save_uploaded_file(file, full_path)
        
        save_success = await safe_file_operation("file_save", save_file)
        if not save_success:
            raise FileUploadError("文件保存失败")
        
        # 7. 提取元数据
        final_title = title if title else file.filename
        try:
            metadata = extract_metadata_from_file(full_path, file.filename)
            if not title and metadata.get("title"):
                final_title = metadata.get("title")
        except Exception as e:
            logger.warning(f"元数据提取失败，使用默认标题: {e}")
        
        # 8. 创建数据库记录
        try:
            literature = Literature(
                title=final_title,
                filename=file.filename,
                file_path=relative_path,
                file_size=file_info["file_size"],
                file_type=file_info["file_type"],
                uploaded_by=current_user.id,
                research_group_id=group_id
            )
            
            db.add(literature)
            db.commit()
            db.refresh(literature)
            
        except Exception as e:
            # 如果数据库操作失败，尝试删除已保存的文件
            try:
                import os
                if os.path.exists(full_path):
                    os.remove(full_path)
            except:
                pass
            raise e
        
        # 9. 记录成功日志
        log_success("literature_upload", current_user.id, {
            "literature_id": literature.id,
            "title": final_title,
            "filename": file.filename,
            "file_size": file_info["file_size"],
            "group_id": group_id
        })
        
        # 10. 返回上传结果
        return FileUploadResponse(
            message="文献上传成功",
            literature_id=literature.id,
            title=final_title,
            filename=file.filename,
            file_size=file_info["file_size"]
        )
        
    except (ValidationError, PermissionError, FileUploadError) as e:
        # 处理已知的业务异常
        raise handle_file_upload_error(e, file.filename, current_user.id)
    
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    
    except Exception as e:
        # 处理未知异常
        log_error("literature_upload", e, current_user.id, operation_info)
        raise handle_file_upload_error(e, file.filename, current_user.id)

@app.get("/literature/public/{group_id}", response_model=LiteratureListResponse)
def get_group_literature(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定研究组的公共文献列表 - 增强版错误处理
    """
    try:
        # 1. 验证用户是否为指定研究组成员
        try:
            require_group_membership(current_user.id, group_id, db)
        except HTTPException as e:
            raise handle_permission_error(Exception(e.detail), "literature_list", current_user.id)
        
        # 2. 查询该研究组的所有活跃文献
        literature_query = db.query(Literature, User).join(
            User, Literature.uploaded_by == User.id
        ).filter(
            Literature.research_group_id == group_id,
            Literature.status == 'active'
        ).order_by(Literature.upload_time.desc())
        
        literature_records = literature_query.all()
        
        # 3. 构建响应数据
        literature_list = []
        for lit, uploader in literature_records:
            literature_list.append(LiteratureListItem(
                id=lit.id,
                title=lit.title,
                filename=lit.filename,
                file_size=lit.file_size,
                file_type=lit.file_type,
                upload_time=lit.upload_time,
                uploader_name=uploader.username
            ))
        
        log_success("literature_list", current_user.id, {
            "group_id": group_id,
            "literature_count": len(literature_list)
        })
        
        return LiteratureListResponse(
            total=len(literature_list),
            literature=literature_list
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        log_error("literature_list", e, current_user.id, {"group_id": group_id})
        raise HTTPException(status_code=500, detail="获取文献列表失败")

@app.get("/user/groups")
def get_user_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户所属的研究组列表
    """
    try:
        # 查询用户所属的研究组
        groups = db.query(ResearchGroup).join(
            UserResearchGroup, ResearchGroup.id == UserResearchGroup.group_id
        ).filter(UserResearchGroup.user_id == current_user.id).all()
        
        group_list = []
        for group in groups:
            group_list.append({
                "id": group.id,
                "name": group.name,
                "institution": group.institution,
                "description": group.description,
                "research_area": group.research_area
            })
        
        log_success("user_groups", current_user.id, {"group_count": len(group_list)})
        
        return {
            "total": len(group_list),
            "groups": group_list
        }
        
    except Exception as e:
        log_error("user_groups", e, current_user.id)
        raise HTTPException(status_code=500, detail="获取研究组列表失败")
    
# 添加软删除文献接口
@app.delete("/literature/{literature_id}")
async def delete_literature(
    literature_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """软删除文献"""
    try:
        from app.utils.literature_manager import soft_delete_literature
        
        success = soft_delete_literature(literature_id, current_user.id, db, reason)
        
        if success:
            logger.info(f"文献删除成功: {literature_id} by {current_user.username}")
            return {"message": "文献删除成功", "literature_id": literature_id}
        else:
            raise HTTPException(status_code=404, detail="文献不存在或无权删除")
            
    except Exception as e:
        logger.error(f"删除文献失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文献失败: {str(e)}")

# 恢复已删除文献接口
@app.post("/literature/{literature_id}/restore")
async def restore_literature(
    literature_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """恢复已删除的文献"""
    try:
        from app.utils.literature_manager import restore_literature
        
        success = restore_literature(literature_id, current_user.id, db)
        
        if success:
            logger.info(f"文献恢复成功: {literature_id} by {current_user.username}")
            return {"message": "文献恢复成功", "literature_id": literature_id}
        else:
            raise HTTPException(status_code=404, detail="文献不存在或无权恢复")
            
    except Exception as e:
        logger.error(f"恢复文献失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复文献失败: {str(e)}")

# 获取已删除文献列表接口
@app.get("/literature/deleted/{group_id}")
async def get_deleted_literature(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取研究组的已删除文献列表"""
    try:
        from app.utils.literature_manager import get_deleted_literature
        
        deleted_list = get_deleted_literature(group_id, current_user.id, db)
        
        logger.info(f"获取删除文献列表: group={group_id}, count={len(deleted_list)}")
        return {
            "group_id": group_id,
            "deleted_literature": deleted_list,
            "count": len(deleted_list)
        }
        
    except Exception as e:
        logger.error(f"获取删除文献列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取删除文献列表失败: {str(e)}")

# 获取文献统计信息接口
@app.get("/literature/stats/{group_id}")
async def get_literature_statistics(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取研究组文献统计信息"""
    try:
        from app.utils.literature_manager import get_literature_stats
        from app.utils.auth_helper import verify_group_membership
        
        # 验证用户是否为研究组成员
        if not verify_group_membership(current_user.id, group_id, db):
            raise HTTPException(status_code=403, detail="无权查看该研究组统计信息")
        
        stats = get_literature_stats(group_id, db)
        
        logger.info(f"获取文献统计: group={group_id}, active={stats['active_count']}")
        return {
            "group_id": group_id,
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文献统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文献统计失败: {str(e)}")

# 获取存储统计信息接口
@app.get("/admin/storage/stats")
async def get_storage_statistics(
    current_user: User = Depends(get_current_user)
):
    """获取存储统计信息（管理员功能）"""
    try:
        from app.utils.storage_manager import get_storage_stats, validate_storage
        
        # 简单的管理员验证（实际项目中应该有更严格的权限控制）
        # 这里暂时允许所有登录用户查看
        
        storage_stats = get_storage_stats()
        storage_health = validate_storage()
        
        logger.info(f"获取存储统计: groups={storage_stats['total_groups']}, files={storage_stats['total_files']}")
        return {
            "storage_statistics": storage_stats,
            "storage_health": storage_health
        }
        
    except Exception as e:
        logger.error(f"获取存储统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取存储统计失败: {str(e)}")

# 清理存储接口
@app.post("/admin/storage/cleanup")
async def cleanup_storage(
    current_user: User = Depends(get_current_user)
):
    """清理存储（删除空目录）"""
    try:
        from app.utils.storage_manager import cleanup_storage
        
        cleaned_dirs = cleanup_storage()
        
        logger.info(f"存储清理完成: 清理了 {len(cleaned_dirs)} 个空目录")
        return {
            "message": "存储清理完成",
            "cleaned_directories": cleaned_dirs,
            "count": len(cleaned_dirs)
        }
        
    except Exception as e:
        logger.error(f"存储清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"存储清理失败: {str(e)}")
    
@app.get("/literature/view/file/{literature_id}")
async def view_literature_file(
    literature_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查看/下载文献文件
    提供文献文件的安全下载和流式传输
    """
    try:
        # 1. 获取文献信息并验证权限
        literature = get_literature_with_permission(literature_id, current_user.id, db)
        
        # 2. 验证文件是否存在
        if not verify_file_exists(literature.file_path):
            log_error("file_view", Exception("文件不存在"), current_user.id, {
                "literature_id": literature_id,
                "file_path": literature.file_path
            })
            raise HTTPException(status_code=404, detail="文件不存在，可能已被移动或删除")
        
        # 3. 获取正确的Content-Type
        content_type = get_content_type(literature.file_path)
        
        # 4. 记录访问日志
        log_success("file_view", current_user.id, {
            "literature_id": literature_id,
            "filename": literature.filename,
            "file_type": literature.file_type
        })
        
        # 5. 返回文件响应
        return FileResponse(
            path=literature.file_path,
            media_type=content_type,
            filename=literature.filename,
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{literature.filename}",
                "Cache-Control": "private, max-age=3600"  # 缓存1小时
            }
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        log_error("file_view", e, current_user.id, {"literature_id": literature_id})
        raise HTTPException(status_code=500, detail="文件访问失败")

@app.get("/literature/detail/{literature_id}")
async def get_literature_detail(
    literature_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取文献详细信息
    返回文献的详细元数据，用于前端显示和处理决策
    """
    try:
        # 1. 获取文献信息并验证权限
        literature = get_literature_with_permission(literature_id, current_user.id, db)
        
        # 2. 获取上传用户信息
        uploader = db.query(User).filter(User.id == literature.uploaded_by).first()
        uploader_name = uploader.username if uploader else "未知用户"
        
        # 3. 获取研究组信息
        group = db.query(ResearchGroup).filter(ResearchGroup.id == literature.research_group_id).first()
        group_name = group.name if group else "未知研究组"
        
        # 4. 检查文件是否存在
        file_exists = verify_file_exists(literature.file_path)
        
        # 5. 构建响应数据
        detail_info = {
            "id": literature.id,
            "title": literature.title,
            "filename": literature.filename,
            "file_type": literature.file_type,
            "file_size": literature.file_size,
            "upload_time": literature.upload_time.isoformat() if literature.upload_time else None,
            "uploaded_by": literature.uploaded_by,
            "uploader_name": uploader_name,
            "research_group_id": literature.research_group_id,
            "group_name": group_name,
            "status": literature.status,
            "file_exists": file_exists,
            "can_view": file_exists and literature.status == 'active',
            "content_type": get_content_type(literature.file_path) if file_exists else None
        }
        
        # 6. 记录访问日志
        log_success("literature_detail", current_user.id, {
            "literature_id": literature_id,
            "title": literature.title
        })
        
        return detail_info
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        log_error("literature_detail", e, current_user.id, {"literature_id": literature_id})
        raise HTTPException(status_code=500, detail="获取文献详情失败")

@app.get("/literature/download/{literature_id}")
async def download_literature_file(
    literature_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    下载文献文件
    强制下载文件而不是在浏览器中打开
    """
    try:
        # 1. 获取文献信息并验证权限
        literature = get_literature_with_permission(literature_id, current_user.id, db)
        
        # 2. 验证文件是否存在
        if not verify_file_exists(literature.file_path):
            raise HTTPException(status_code=404, detail="文件不存在，可能已被移动或删除")
        
        # 3. 获取正确的Content-Type
        content_type = get_content_type(literature.file_path)
        
        # 4. 记录下载日志
        log_success("file_download", current_user.id, {
            "literature_id": literature_id,
            "filename": literature.filename,
            "file_type": literature.file_type
        })
        
        # 5. 返回文件响应（强制下载）
        return FileResponse(
            path=literature.file_path,
            media_type=content_type,
            filename=literature.filename,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{literature.filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("file_download", e, current_user.id, {"literature_id": literature_id})
        raise HTTPException(status_code=500, detail="文件下载失败")