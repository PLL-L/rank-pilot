from pydantic import ConfigDict

from models.config_model import ConfigBase, ConfigTable


class ConfigCreateRequest(ConfigBase):
    model_config = ConfigDict(from_attributes=True)

class ConfigUpdateRequest(ConfigBase):
    model_config = ConfigDict(from_attributes=True)

class ConfigResponse(ConfigBase):
    model_config = ConfigDict(from_attributes=True)
    @classmethod
    def from_db_model(cls, row: ConfigTable) -> "ConfigResponse":
        return cls.model_validate(row)
