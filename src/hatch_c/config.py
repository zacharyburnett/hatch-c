from os import system as system_call
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from .extension import BuildType, HatchCExtension, HatchCPlatform

__all__ = (
    "HatchCBuildConfig",
    "HatchCBuildPlan",
)


class HatchCBuildConfig(BaseModel):
    skip: Optional[bool] = Field(default=False)
    name: Optional[str] = Field(default=None)
    extensions: List[HatchCExtension] = Field(default_factory=list)
    platform: Optional[HatchCPlatform] = Field(
        default_factory=HatchCPlatform.default
    )

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(cls, data, handler):
        if "toolchain" in data:
            data["platform"] = HatchCPlatform.platform_for_toolchain(
                data["toolchain"]
            )
            data.pop("toolchain")
        elif "platform" not in data:
            data["platform"] = HatchCPlatform.default()
        if "cc" in data:
            data["platform"].cc = data["cc"]
            data.pop("cc")
        if "ld" in data:
            data["platform"].ld = data["ld"]
            data.pop("ld")
        model = handler(data)
        return model


class HatchCBuildPlan(HatchCBuildConfig):
    build_type: BuildType = "release"
    commands: List[str] = Field(default_factory=list)

    def generate(self):
        self.commands = []

        for extension in self.extensions:
            compile_flags = self.platform.get_compile_flags(extension, self.build_type)
            link_flags = self.platform.get_link_flags(extension, self.build_type)
            self.commands.append(
                f"{self.platform.cc} {' '.join(extension.sources)} {compile_flags} {link_flags}"
            )

        return self.commands

    def execute(self):
        for command in self.commands:
            ret = system_call(command)
            if ret != 0:
                raise RuntimeError(
                    f"hatch-c build command failed with exit code {ret}: {command}"
                )
        return self.commands

    def cleanup(self):
        if self.platform.platform == "win32":
            for temp_obj in Path(".").glob("*.obj"):
                temp_obj.unlink()
