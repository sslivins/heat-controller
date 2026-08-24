"""Tag CRUD + device tag assignment."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from goodhvac.database import get_db
from goodhvac.models import Tag
from goodhvac.schemas import TagCreate, TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[Tag]:
    result = await db.execute(select(Tag).order_by(Tag.key, Tag.value))
    return list(result.scalars().all())


@router.post("", response_model=TagRead, status_code=201)
async def create_tag(payload: TagCreate, db: AsyncSession = Depends(get_db)) -> Tag:
    tag = Tag(key=payload.key.strip().lower(), value=payload.value.strip())
    db.add(tag)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tag with this key/value already exists") from exc
    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)) -> None:
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    await db.delete(tag)
    await db.commit()
