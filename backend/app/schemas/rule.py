from pydantic import BaseModel, ConfigDict, Field, field_validator


def _reject_blank(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


class RuleCreateRequest(BaseModel):
    keyword: str = Field(..., min_length=1)
    dm_message: str = Field(..., min_length=1)

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str) -> str:
        trimmed = value.strip()
        _reject_blank(trimmed, "keyword")
        return trimmed.lower()

    @field_validator("dm_message")
    @classmethod
    def validate_dm_message(cls, value: str) -> str:
        _reject_blank(value, "dm_message")
        return value


class RuleResponse(BaseModel):
    rule_id: str
    keyword: str
    dm_message: str

    model_config = ConfigDict(from_attributes=True)
