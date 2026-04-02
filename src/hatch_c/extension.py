from __future__ import annotations

from os import environ
from pathlib import Path
from re import match
from shutil import which
from sys import base_exec_prefix, exec_prefix, executable, platform as sys_platform
from sysconfig import get_config_var, get_path
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = (
    "BuildType",
    "CompilerToolchain",
    "Platform",
    "PlatformDefaults",
    "HatchCExtension",
    "HatchCPlatform",
    "_normalize_rpath",
)


BuildType = Literal["debug", "release"]
CompilerToolchain = Literal["gcc", "clang", "msvc"]
Platform = Literal["linux", "darwin", "win32"]
PlatformDefaults = {
    "linux": {"CC": "gcc", "LD": "ld"},
    "darwin": {"CC": "clang", "LD": "ld"},
    "win32": {"CC": "cl", "LD": "link"},
}


class HatchCExtension(BaseModel, validate_assignment=True):
    name: str
    sources: List[str]

    include_dirs: List[str] = Field(default_factory=list, alias="include-dirs")
    include_dirs_linux: List[str] = Field(
        default_factory=list, alias="include-dirs-linux"
    )
    include_dirs_darwin: List[str] = Field(
        default_factory=list, alias="include-dirs-darwin"
    )
    include_dirs_win32: List[str] = Field(
        default_factory=list, alias="include-dirs-win32"
    )

    include_numpy: bool = Field(default=False, alias="include-numpy")

    library_dirs: List[str] = Field(default_factory=list, alias="library-dirs")
    library_dirs_linux: List[str] = Field(
        default_factory=list, alias="library-dirs-linux"
    )
    library_dirs_darwin: List[str] = Field(
        default_factory=list, alias="library-dirs-darwin"
    )
    library_dirs_win32: List[str] = Field(
        default_factory=list, alias="library-dirs-win32"
    )

    libraries: List[str] = Field(default_factory=list)
    libraries_linux: List[str] = Field(default_factory=list, alias="libraries-linux")
    libraries_darwin: List[str] = Field(default_factory=list, alias="libraries-darwin")
    libraries_win32: List[str] = Field(default_factory=list, alias="libraries-win32")

    extra_compile_args: List[str] = Field(
        default_factory=list, alias="extra-compile-args"
    )
    extra_compile_args_linux: List[str] = Field(
        default_factory=list, alias="extra-compile-args-linux"
    )
    extra_compile_args_darwin: List[str] = Field(
        default_factory=list, alias="extra-compile-args-darwin"
    )
    extra_compile_args_win32: List[str] = Field(
        default_factory=list, alias="extra-compile-args-win32"
    )

    extra_link_args: List[str] = Field(default_factory=list, alias="extra-link-args")
    extra_link_args_linux: List[str] = Field(
        default_factory=list, alias="extra-link-args-linux"
    )
    extra_link_args_darwin: List[str] = Field(
        default_factory=list, alias="extra-link-args-darwin"
    )
    extra_link_args_win32: List[str] = Field(
        default_factory=list, alias="extra-link-args-win32"
    )

    extra_objects: List[str] = Field(default_factory=list, alias="extra-objects")
    extra_objects_linux: List[str] = Field(
        default_factory=list, alias="extra-objects-linux"
    )
    extra_objects_darwin: List[str] = Field(
        default_factory=list, alias="extra-objects-darwin"
    )
    extra_objects_win32: List[str] = Field(
        default_factory=list, alias="extra-objects-win32"
    )

    define_macros: List[str] = Field(default_factory=list, alias="define-macros")
    define_macros_linux: List[str] = Field(
        default_factory=list, alias="define-macros-linux"
    )
    define_macros_darwin: List[str] = Field(
        default_factory=list, alias="define-macros-darwin"
    )
    define_macros_win32: List[str] = Field(
        default_factory=list, alias="define-macros-win32"
    )

    undef_macros: List[str] = Field(default_factory=list, alias="undef-macros")
    undef_macros_linux: List[str] = Field(
        default_factory=list, alias="undef-macros-linux"
    )
    undef_macros_darwin: List[str] = Field(
        default_factory=list, alias="undef-macros-darwin"
    )
    undef_macros_win32: List[str] = Field(
        default_factory=list, alias="undef-macros-win32"
    )

    export_symbols: List[str] = Field(default_factory=list, alias="export-symbols")
    depends: List[str] = Field(default_factory=list)

    py_limited_api: Optional[str] = Field(default="", alias="py-limited-api")

    @field_validator("py_limited_api", mode="before")
    @classmethod
    def check_py_limited_api(cls, value: Any) -> Any:
        if value:
            if not match(r"cp3\d", value):
                raise ValueError("py-limited-api must be in the form of cp3X")
        return value

    def qualified_name(self, platform):
        if platform == "win32":
            suffix = "pyd"
        elif platform == "darwin":
            suffix = "so"
        else:
            suffix = "so"
        if self.py_limited_api and platform != "win32":
            return f"{self.name}.abi3.{suffix}"
        return f"{self.name}.{suffix}"

    def effective_link_args(self, platform: Platform) -> List[str]:
        """merge generic with platform-specific"""
        args = list(self.extra_link_args)
        if platform == "linux":
            args.extend(self.extra_link_args_linux)
        elif platform == "darwin":
            args.extend(self.extra_link_args_darwin)
        elif platform == "win32":
            args.extend(self.extra_link_args_win32)
        return args

    def effective_include_dirs(self, platform: Platform) -> List[str]:
        """merge generic with platform-specific"""
        dirs = list(self.include_dirs)
        if platform == "linux":
            dirs.extend(self.include_dirs_linux)
        elif platform == "darwin":
            dirs.extend(self.include_dirs_darwin)
        elif platform == "win32":
            dirs.extend(self.include_dirs_win32)
        if self.include_numpy:
            try:
                import numpy
            except ImportError:
                raise ImportError("numpy not found; is it in `build-system.requires`?")
            dirs.extend(numpy.get_include())
        return dirs

    def effective_library_dirs(self, platform: Platform) -> List[str]:
        """merge generic with platform-specific"""
        dirs = list(self.library_dirs)
        if platform == "linux":
            dirs.extend(self.library_dirs_linux)
        elif platform == "darwin":
            dirs.extend(self.library_dirs_darwin)
        elif platform == "win32":
            dirs.extend(self.library_dirs_win32)
        return dirs

    def effective_libraries(self, platform: Platform) -> List[str]:
        """merge generic with platform-specific"""
        libs = list(self.libraries)
        if platform == "linux":
            libs.extend(self.libraries_linux)
        elif platform == "darwin":
            libs.extend(self.libraries_darwin)
        elif platform == "win32":
            libs.extend(self.libraries_win32)
        return libs

    def effective_compile_args(self, platform: Platform) -> List[str]:
        """merge generic with platform-specific"""
        args = list(self.extra_compile_args)
        if platform == "linux":
            args.extend(self.extra_compile_args_linux)
        elif platform == "darwin":
            args.extend(self.extra_compile_args_darwin)
        elif platform == "win32":
            args.extend(self.extra_compile_args_win32)
        return args

    def effective_extra_objects(self, platform: Platform) -> List[str]:
        """merge generic with platform-specific"""
        objs = list(self.extra_objects)
        if platform == "linux":
            objs.extend(self.extra_objects_linux)
        elif platform == "darwin":
            objs.extend(self.extra_objects_darwin)
        elif platform == "win32":
            objs.extend(self.extra_objects_win32)
        return objs

    def effective_define_macros(self, platform: Platform) -> List[str]:
        """merge generic with platform-specific"""
        macros = list(self.define_macros)
        if platform == "linux":
            macros.extend(self.define_macros_linux)
        elif platform == "darwin":
            macros.extend(self.define_macros_darwin)
        elif platform == "win32":
            macros.extend(self.define_macros_win32)
        return macros

    def effective_undef_macros(self, platform: Platform) -> List[str]:
        """merge generic with platform-specific"""
        macros = list(self.undef_macros)
        if platform == "linux":
            macros.extend(self.undef_macros_linux)
        elif platform == "darwin":
            macros.extend(self.undef_macros_darwin)
        elif platform == "win32":
            macros.extend(self.undef_macros_win32)
        return macros


def _normalize_rpath(value: str, platform: Platform) -> str:
    r"""Translate and escape rpath values for the target platform.

    - On macOS (darwin): ``$ORIGIN`` is replaced with ``@loader_path``.
    - On Linux: ``@loader_path`` is replaced with ``$ORIGIN``, and
      ``$ORIGIN`` is escaped as ``\$ORIGIN`` so that ``os.system()``
      (which invokes a shell) passes it through literally.
    - On Windows: no transformation is applied (Windows does not use
      rpath).
    """
    if platform == "darwin":
        # Handle already-escaped \$ORIGIN first, then plain $ORIGIN
        value = value.replace(r"\$ORIGIN", "@loader_path")
        value = value.replace("$ORIGIN", "@loader_path")
    elif platform == "linux":
        # Translate macOS rpath to Linux equivalent
        value = value.replace("@loader_path", "$ORIGIN")
        # Escape $ORIGIN for shell safety (os.system runs through bash)
        value = value.replace("$ORIGIN", r"\$ORIGIN")
    return value


class HatchCPlatform(BaseModel):
    cc: str
    ld: str
    platform: Platform
    toolchain: CompilerToolchain
    disable_ccache: bool = False

    @staticmethod
    def default() -> HatchCPlatform:
        CC = environ.get("CC", PlatformDefaults[sys_platform]["CC"])
        LD = environ.get("LD", PlatformDefaults[sys_platform]["LD"])
        if "gcc" in CC:
            toolchain = "gcc"
        elif "clang" in CC:
            toolchain = "clang"
        elif "cl" in CC:
            toolchain = "msvc"
        # Fallback to platform defaults
        elif sys_platform == "linux":
            toolchain = "gcc"
        elif sys_platform == "darwin":
            toolchain = "clang"
        elif sys_platform == "win32":
            toolchain = "msvc"
        else:
            toolchain = "gcc"

        # TODO:
        # https://github.com/rui314/mold/issues/647
        # if which("ld.mold"):
        #     LD = which("ld.mold")
        # elif which("ld.lld"):
        #     LD = which("ld.lld")
        return HatchCPlatform(cc=CC, ld=LD, platform=sys_platform, toolchain=toolchain)

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(cls, data, handler):
        model = handler(data)
        if which("ccache") and not model.disable_ccache:
            if model.toolchain in ["gcc", "clang"]:
                if not model.cc.startswith("ccache "):
                    model.cc = f"ccache {model.cc}"
                if not model.cxx.startswith("ccache "):
                    model.cxx = f"ccache {model.cxx}"
        return model

    @staticmethod
    def platform_for_toolchain(toolchain: CompilerToolchain) -> HatchCPlatform:
        platform = HatchCPlatform.default()
        platform.toolchain = toolchain
        return platform

    def get_compile_flags(
        self, extension: HatchCExtension, build_type: BuildType = "release"
    ) -> str:
        flags = ""

        # Get effective platform-specific values
        effective_include_dirs = extension.effective_include_dirs(self.platform)
        effective_compile_args = extension.effective_compile_args(self.platform)
        effective_define_macros = extension.effective_define_macros(self.platform)
        effective_undef_macros = extension.effective_undef_macros(self.platform)
        effective_extra_objects = extension.effective_extra_objects(self.platform)
        effective_link_args = extension.effective_link_args(self.platform)

        # Python.h
        effective_include_dirs.append(get_path("include"))

        if extension.py_limited_api:
            effective_define_macros.append(
                f"Py_LIMITED_API=0x0{extension.py_limited_api[2]}0{hex(int(extension.py_limited_api[3:]))[2:]}00f0"
            )

        # Toolchain-specific flags
        if self.toolchain == "gcc":
            flags += " " + " ".join(f"-I{d}" for d in effective_include_dirs)
            flags += " -fPIC"
            flags += " " + " ".join(effective_compile_args)
            flags += " " + " ".join(f"-D{macro}" for macro in effective_define_macros)
            flags += " " + " ".join(f"-U{macro}" for macro in effective_undef_macros)
            if extension.std:
                flags += f" -std={extension.std}"
        elif self.toolchain == "clang":
            flags += " ".join(f"-I{d}" for d in effective_include_dirs)
            flags += " -fPIC"
            flags += " " + " ".join(effective_compile_args)
            flags += " " + " ".join(f"-D{macro}" for macro in effective_define_macros)
            flags += " " + " ".join(f"-U{macro}" for macro in effective_undef_macros)
            if extension.std:
                flags += f" -std={extension.std}"
        elif self.toolchain == "msvc":
            flags += " ".join(f"/I{d}" for d in effective_include_dirs)
            flags += " " + " ".join(effective_compile_args)
            flags += " " + " ".join(effective_link_args)
            flags += " " + " ".join(effective_extra_objects)
            flags += " " + " ".join(f"/D{macro}" for macro in effective_define_macros)
            flags += " " + " ".join(f"/U{macro}" for macro in effective_undef_macros)
            flags += " /EHsc /DWIN32"
            if extension.std:
                std = extension.std
                flags += f" /std:{std}"
        # clean
        while flags.count("  "):
            flags = flags.replace("  ", " ")
        return flags

    def get_link_flags(
        self, extension: HatchCExtension, build_type: BuildType = "release"
    ) -> str:
        flags = ""
        effective_link_args = extension.effective_link_args(self.platform)
        effective_extra_objects = extension.effective_extra_objects(self.platform)
        effective_libraries = extension.effective_libraries(self.platform)
        effective_library_dirs = extension.effective_library_dirs(self.platform)

        # Normalize rpath values ($ORIGIN <-> @loader_path) and escape for shell
        effective_link_args = [
            _normalize_rpath(arg, self.platform) for arg in effective_link_args
        ]

        if self.toolchain == "gcc":
            flags += " -shared"
            flags += " " + " ".join(effective_link_args)
            flags += " " + " ".join(effective_extra_objects)
            flags += " " + " ".join(f"-l{lib}" for lib in effective_libraries)
            flags += " " + " ".join(f"-L{lib}" for lib in effective_library_dirs)
            flags += f" -o {extension.qualified_name(self.platform)}"
            if self.platform == "darwin":
                flags += " -undefined dynamic_lookup"
            if "mold" in self.ld:
                flags += f" -fuse-ld={self.ld}"
            elif "lld" in self.ld:
                flags += " -fuse-ld=lld"
        elif self.toolchain == "clang":
            flags += " -shared"
            flags += " " + " ".join(effective_link_args)
            flags += " " + " ".join(effective_extra_objects)
            flags += " " + " ".join(f"-l{lib}" for lib in effective_libraries)
            flags += " " + " ".join(f"-L{lib}" for lib in effective_library_dirs)
            flags += f" -o {extension.qualified_name(self.platform)}"
            if self.platform == "darwin":
                flags += " -undefined dynamic_lookup"
            if "mold" in self.ld:
                flags += f" -fuse-ld={self.ld}"
            elif "lld" in self.ld:
                flags += " -fuse-ld=lld"
        elif self.toolchain == "msvc":
            flags += " " + " ".join(effective_link_args)
            flags += " " + " ".join(effective_extra_objects)
            flags += " /LD"
            flags += f" /Fe:{extension.qualified_name(self.platform)}"
            flags += " /link /DLL"
            # Add Python libs directory - check multiple possible locations
            # In virtual environments, sys.executable is in the venv, but pythonXX.lib
            # lives under the base Python installation's 'libs' directory.
            python_libs_paths = [
                Path(executable).parent / "libs",  # Standard Python install
                Path(executable).parent.parent / "libs",  # Some virtualenv layouts
                Path(get_config_var("installed_base") or "")
                / "libs",  # sysconfig approach
                Path(exec_prefix) / "libs",  # exec_prefix approach
                Path(base_exec_prefix) / "libs",  # base_exec_prefix approach
            ]
            for libs_path in python_libs_paths:
                if libs_path.exists():
                    flags += f" /LIBPATH:{str(libs_path)}"
                    break
            flags += " " + " ".join(f"{lib}.lib" for lib in effective_libraries)
            flags += " " + " ".join(f"/LIBPATH:{lib}" for lib in effective_library_dirs)
        # clean
        while flags.count("  "):
            flags = flags.replace("  ", " ")
        return flags
