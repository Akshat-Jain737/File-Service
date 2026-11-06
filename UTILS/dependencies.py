from typing import Annotated
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from database import get_session
from SERVICES.data_services import DataServices


def get_data_service(session: AsyncSession = Depends(get_session)) -> DataServices:
    return DataServices(session)


dep = Annotated[DataServices, Depends(get_data_service)]
