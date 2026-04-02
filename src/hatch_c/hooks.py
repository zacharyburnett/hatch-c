from typing import Type

from hatchling.plugin import hookimpl

from .plugin import HatchCBuildHook


@hookimpl
def hatch_register_build_hook() -> Type[HatchCBuildHook]:
    return HatchCBuildHook
