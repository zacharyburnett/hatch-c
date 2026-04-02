from __future__ import annotations

from pathlib import Path
from platform import machine as platform_machine
from sys import platform as sys_platform, version_info
from typing import Any

from hatch_build import parse_extra_args_model
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .config import HatchCBuildConfig, HatchCBuildPlan
from .utils import import_string

__all__ = ("HatchCBuildHook",)


class HatchCBuildHook(BuildHookInterface[HatchCBuildConfig]):
    PLUGIN_NAME = "hatch-c"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        # Log some basic information
        project_name = self.metadata.config["project"]["name"]

        # Only run if creating wheel
        # TODO: Add support for specify sdist-plan
        if self.target_name != "wheel":
            return

        # Get build config class or use default
        build_config_class = import_string(self.config["build-config-class"]) if "build-config-class" in self.config else HatchCppBuildConfig

        # Instantiate build config
        config = build_config_class(name=project_name, **self.config)

        # Get build plan class or use default
        build_plan_class = import_string(self.config["build-plan-class"]) if "build-plan-class" in self.config else HatchCppBuildPlan

        # Instantiate builder
        build_plan = build_plan_class(**config.model_dump())

        # Parse override args
        parse_extra_args_model(build_plan)

        # Generate commands
        build_plan.generate()

        if build_plan.skip:
            return

        # Execute build plan
        build_plan.execute()

        # Perform any cleanup actions
        build_plan.cleanup()

        if build_plan.extension:
            # force include libraries
            for extension in build_plan.extension:
                name = extension.get_qualified_name(build_plan.platform.platform)
                build_data["force_include"][name] = name

            build_data["pure_python"] = False
            machine = platform_machine()
            version_major = version_info.major
            version_minor = version_info.minor
            if "darwin" in sys_platform:
                os_name = "macosx_11_0"
            elif "linux" in sys_platform:
                os_name = "linux"
            else:
                os_name = "win"

            if all([lib.py_limited_api for lib in build_plan.extension]):
                build_data["tag"] = f"cp{version_major}{version_minor}-abi3-{os_name}_{machine}"
            else:
                build_data["tag"] = f"cp{version_major}{version_minor}-cp{version_major}{version_minor}-{os_name}_{machine}"
        else:
            build_data["pure_python"] = False
            machine = platform_machine()
            version_major = version_info.major
            version_minor = version_info.minor
            # TODO abi3
            if "darwin" in sys_platform:
                os_name = "macosx_11_0"
            elif "linux" in sys_platform:
                os_name = "linux"
            else:
                os_name = "win"
            build_data["tag"] = f"cp{version_major}{version_minor}-cp{version_major}{version_minor}-{os_name}_{machine}"

            # force include libraries
            for path in Path(".").rglob("*"):
                if path.is_dir():
                    continue
                if str(path).startswith(str(build_plan.cmake.build)) or str(path).startswith("dist"):
                    continue
                if path.suffix in (".pyd", ".dll", ".so", ".dylib"):
                    build_data["force_include"][str(path)] = str(path)

