# Command line build script for SoSSim, with various flags to control what stages are executed.

import argparse
from pathlib import Path
import os

import mypy.api
import pdoc

if __name__ == "__main__":
    # Parse the command line arguments and store them in args.
    parser = argparse.ArgumentParser(description = "Build the SoSSim simulator.")
    parser.add_argument("--typecheck",  default = False, action = argparse.BooleanOptionalAction, help = "Run code typecheck")
    parser.add_argument("--docs",       default = False, action = argparse.BooleanOptionalAction, help = "Generate documentation")
    parser.add_argument("--pyconfig",   default = False, action = argparse.BooleanOptionalAction, help = "Generate pyscript configuration file")
    parser.add_argument("--wheel",      default = False, action = argparse.BooleanOptionalAction, help = "Build a wheel file for the sossim package")
    parser.add_argument("--all",        default = False, action = "store_true",                   help = "Run all build steps")

    args = parser.parse_args()

    source_dir = Path("sossim")
    app_dir = Path("app")

    # Build steps

    # Typechecking
    if args.typecheck or args.all:
        print("Typecheck code")
        for file in source_dir.glob("**/*.py"):
            # Type check all Python files, except those in the mesa subdirectory.
            if file.parent.name != "mesa":
                print(f"Checking {file}")
                result = mypy.api.run([str(file), "--follow-imports", "silent"])
                if result[0]:
                    print(result[0])
                if result[1]:
                    print("\nErrors\n:", result[1])

    # Documentation
    if args.docs or args.all:
        print("Generate documentation")
        target_dir = Path("documentation")
        # Remove existing files before generating new ones.
        for file in target_dir.glob("*"):
            file.unlink()
        # Configure and run pdoc on selected files
        pdoc.render.configure(docformat = "google", mermaid = True)
        modules = list(source_dir.glob("*.py"))
        # The following code is based on pdoc.pdoc, but modified to skip files that causes an error.
        all_modules = {}
        for module_name in pdoc.extract.walk_specs(modules):
            try:
                all_modules[module_name] = pdoc.doc.Module.from_name(module_name)
            except:
                print("Cannot document module", module_name)

        for module in all_modules.values():
            out = pdoc.render.html_module(module, all_modules)
            outfile = target_dir / f"{module.fullname.replace('.', '/')}.html"
            outfile.parent.mkdir(parents=True, exist_ok=True)
            outfile.write_bytes(out.encode())

        if index := pdoc.render.html_index(all_modules):
            (target_dir / "index.html").write_bytes(index.encode())

        if search := pdoc.render.search_index(all_modules):
            (target_dir / "search.js").write_bytes(search.encode())

    # Pyscript configuration file
    if args.pyconfig or args.all:
        print("Generate pyconfig.toml file")
        # Generate list of packages from requirements.txt
        with open("requirements.txt") as file:
            packages = file.readlines()
        # Remove mesa from the list of packages, since it will be loaded separately using micropip
        packages = [pkg for pkg in packages if not pkg.startswith("mesa")]
        # Add the domed package to the package list
        packages.append("domed")
        # Add the sossim package wheel file to the package list
        packages.append("../dist/sossim-0.1.0-py2.py3-none-any.whl")
        # Clean the package representation and convert to a string
        packages = ", ".join(['"' + pkg.strip() + '"' for pkg in packages])
        # Generate the output
        with (app_dir / "pyconfig.toml").open("w") as f:
            f.write("# Pyscript configuration file generated by build.py\n")
            f.write(f"packages = [{packages}]\n\n")
            f.write("terminal = false\n\n")
            f.write("[splashscreen]\n")
            f.write("enabled = false")

    # Wheel file for sossim package
    if args.wheel or args.all:
        print("Generating wheel file")
        os.system("flit build --format wheel")