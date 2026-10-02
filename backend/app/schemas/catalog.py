from pydantic import BaseModel, ConfigDict


class DomainBase(BaseModel):
    name: str
    slug: str
    description: str | None = None
    is_active: bool


class DomainResponse(DomainBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CategoryBase(BaseModel):
    name: str
    slug: str
    description: str | None = None
    is_active: bool


class CategoryResponse(CategoryBase):
    id: int
    domain_id: int

    model_config = ConfigDict(from_attributes=True)


class SkillBase(BaseModel):
    name: str
    slug: str
    description: str | None = None
    is_active: bool


class SkillResponse(SkillBase):
    id: int
    category_id: int

    model_config = ConfigDict(from_attributes=True)


class CompetencyBase(BaseModel):
    name: str
    description: str | None = None
    target_default: int
    is_active: bool


class CompetencyResponse(CompetencyBase):
    id: int
    skill_id: int

    model_config = ConfigDict(from_attributes=True)