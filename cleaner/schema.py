from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class FieldProcessingConfig(BaseModel):
    """Configuration for processing a single field in the data cleaning pipeline."""

    type: str = Field(
        ...,
        description="Type of the field (numeric, text, structured, categorical, datetime)",
    )
    options: Dict = Field(
        default_factory=dict, description="Options for processing this field type"
    )
    preprocessing: List[str] = Field(
        default_factory=list, description="List of preprocessing steps to apply"
    )
    preserve_raw: bool = Field(
        default=False,
        description="Whether to preserve the raw (but parsed) version of the field",
    )
    min_token_length: int = Field(
        default=3,
        description="Minimum length for tokens in structured fields",
    )
    add_norm_column: bool = Field(
        default=False,
        description="Whether to add a *_norm column for this field",
    )

    validation: Optional[Dict] = Field(
        default=None, description="Validation rules for this field"
    )
    required_for_model: bool = Field(
        default=True,
        description="Whether this field is required for Pydantic model creation",
    )

    class Config:
        extra = "allow"
