
import hashlib
from typing import Union
from fastapi import Depends, APIRouter, UploadFile, HTTPException

from pydantic import UUID4

from app.core.minio import upload_file_to_minio
from ..schemas import Gpt4AllPretrained, Gpt4AllPretrainedCreate, Gpt4AllPretrainedUpdate
from app.dependencies import get_db, get_minio
from sqlalchemy.orm import Session
from .. import crud
from ..models.gpt4all_pretrained import Gpt4AllPretrainedModel
from app.core.errors import HTTPValidationError
from aiofiles import open as open_aio
from minio import Minio



router = APIRouter(
    prefix="/pretrained"
)


@router.post(
    "/",
    response_model=Union[Gpt4AllPretrained, HTTPValidationError],
    responses={'422': {'model': HTTPValidationError}},
    summary="Create gpt4all Pretrained Model object",
    response_description="Created Pretrained Model object"
)
def create_gpt4all_pretrained_object_post(gpt4all_pretrained_obj: Gpt4AllPretrainedCreate, db: Session = Depends(get_db)) -> (
    Union[Gpt4AllPretrained, HTTPValidationError]
):
    """
    Create GPT4All Pretrained Model object.
    """

    # check to make sure sha256 doesn't already exist
    obj_by_sha: Gpt4AllPretrainedModel = crud.gpt4all_pretrained.get_by_sha256(
        db, sha256=gpt4all_pretrained_obj.sha256)

    if obj_by_sha:
        raise HTTPException(status_code=400, detail="sha256 already exists")

    # pydantic handles validation
    new_gpt4all_pretrained_obj: Gpt4AllPretrainedModel = crud.gpt4all_pretrained.create(
        db, obj_in=gpt4all_pretrained_obj)

    return new_gpt4all_pretrained_obj

@router.post(
    "/{id}/upload/",
    response_model=Union[Gpt4AllPretrained, HTTPValidationError],
    responses={'422': {'model': HTTPValidationError}},
    summary="Upload gpt4all Pretrained Model Binary",
    response_description="Uploaded Pretrained Model Binary"
)
async def upload_gpt4all_post(new_file: UploadFile, id: UUID4, db: Session = Depends(get_db), s3: Minio = Depends(get_minio)) -> (
    Union[Gpt4AllPretrained, HTTPValidationError]
):
    """
    Upload gpt4all Pretrained Model Binary.

    - **new_file**: Required.  The file to upload.
    """

    # check to make sure id exists
    gpt4all_pretrained_obj: Gpt4AllPretrainedModel = crud.gpt4all_pretrained.get(
        db, id)
    if not gpt4all_pretrained_obj:
        raise HTTPException(status_code=422, detail="gpt4all Pretrained Model not found")

    # check for hash
    if not gpt4all_pretrained_obj.sha256:
        raise HTTPException(status_code=422, detail="gpt4all Pretrained Model hash not found")

    # validate sha256 hash against file
    sha256_hash = hashlib.sha256()
    while chunk := await new_file.read(8192):
        sha256_hash.update(chunk)
    if sha256_hash.hexdigest() != gpt4all_pretrained_obj.sha256:
        raise HTTPException(status_code=422, detail="SHA256 hash mismatch")

    # upload to minio
    upload_file_to_minio(file=new_file, id=id, s3=s3)

    # update the object in db and return
    new_gpt4all_pretrained_obj: Gpt4AllPretrainedModel = crud.gpt4all_pretrained.update(
        db, db_obj=gpt4all_pretrained_obj, obj_in=Gpt4AllPretrainedUpdate(uploaded=True))

    return new_gpt4all_pretrained_obj
