import os
import shlex

from pytest_testconfig import config as py_config
from pytest import Item
from pyhelper_utils.shell import run_command

from utilities.exceptions import InvalidArguments
from utilities.infra import get_rhods_operator_installed_csv


def get_must_gather_base_dir() -> str:
    return py_config["must_gather_base_dir"]


def get_must_gather_collector_base_directory() -> str:
    return py_config["must_gather_collector"]["must_gather_base_directory"]


def set_must_gather_collector_directory(item: Item, directory_path: str) -> None:
    must_gather_dict = py_config["must_gather_collector"]
    must_gather_dict["collector_directory"] = prepare_pytest_item_data_dir(item=item, output_dir=directory_path)


def get_must_gather_collector_dir() -> str:
    must_gather_dict = py_config["must_gather_collector"]
    return must_gather_dict.get(
        "collector_directory",
        must_gather_dict["must_gather_base_dir"],
    )


def set_must_gather_collector_values() -> str:
    py_config["must_gather_collector"] = {
        "must_gather_base_directory": get_must_gather_base_dir(),
    }
    return py_config["must_gather_collector"]


def prepare_pytest_item_data_dir(item: Item, output_dir: str) -> str:
    """
    Prepare output directory for pytest item

    Example:
        item.fspath= "/home/user/git/<tests-repo>/tests/<test_dir>/test_something.py"
        must-gather-base-dir = "must-gather-base-dir"
        item.name = "test1"
        item_dir_log = "must-gather-base-dir/test_dir/test_something/test1"
    """
    item_cls_name = item.cls.__name__ if item.cls else ""
    tests_path = item.session.config.inicfg.get("testpaths")
    assert tests_path, "pytest.ini must include testpaths"

    fspath_split_str = "/" if tests_path != os.path.split(item.fspath.dirname)[1] else ""
    item_dir_log = os.path.join(
        output_dir,
        item.fspath.dirname.split(f"/{tests_path}{fspath_split_str}")[-1],
        item.fspath.basename.partition(".py")[0],
        item_cls_name,
        item.name,
    )
    os.makedirs(item_dir_log, exist_ok=True)
    return item_dir_log


def get_must_gather_output_dir(must_gather_path: str) -> str:
    for item in os.listdir(must_gather_path):
        new_path = os.path.join(must_gather_path, item)
        if os.path.isdir(new_path):
            return new_path
    raise FileNotFoundError(f"No log directory was created in '{must_gather_path}'")


def run_must_gather(
    image_url: str = "",
    target_dir: str = "",
    since: str = "1m",
    component_name: str = "",
    namespaces_dict: dict[str, str] | None = None,
) -> str:
    if component_name and namespaces_dict:
        raise InvalidArguments("component name and namespaces can't be passed together")

    must_gather_command = "oc adm must-gather"
    if target_dir:
        must_gather_command += f"{must_gather_command} --dest-dir={target_dir}"
    if since:
        must_gather_command += f"{must_gather_command} --since={since}"
    if image_url:
        must_gather_command += f"{must_gather_command} --image={image_url}"
        if component_name:
            must_gather_command += f"{must_gather_command} -- 'export COMPONENT={component_name}; /usr/bin/gather' "
        elif namespaces_dict:
            namespace_str = ""
            if namespaces_dict.get("operator"):
                namespace_str += f"export OPERATOR_NAMESPACE={namespaces_dict['operator']};"
            if namespaces_dict.get("notebooks"):
                namespace_str += f"export NOTEBOOKS_NAMESPACE={namespaces_dict['notebooks']};"
            if namespaces_dict.get("monitoring"):
                namespace_str += f"export MONITORING_NAMESPACE={namespaces_dict['monitoring']};"
            if namespaces_dict.get("application"):
                namespace_str += f"export APPLICATIONS_NAMESPACE={namespaces_dict['application']};"
            if namespaces_dict.get("model_registries"):
                namespace_str += f"export MODEL_REGISTRIES_NAMESPACE={namespaces_dict['model_registries']};"
            if namespaces_dict.get("ossm"):
                namespace_str += f"export OSSM_NS={namespaces_dict['ossm']};"
            if namespaces_dict.get("knative"):
                namespace_str += f"export KNATIVE_NS={namespaces_dict['knative']};"
            if namespaces_dict.get("auth"):
                namespace_str += f"export AUTH_NS={namespaces_dict['auth']};"
            must_gather_command += f"{must_gather_command} /usr/bin/gather"

    return run_command(command=shlex.split(must_gather_command), check=False)[1]


def collect_rhoai_must_gather(target_dir: str, since: int, save_collection_output: bool = True) -> str:
    csv_version = get_rhods_operator_installed_csv()
    must_gather_image = f"quay.io/repository/modh/must-gather:rhoai-{csv_version.major}.{csv_version.minor}"
    output = run_must_gather(image_url=must_gather_image, target_dir=target_dir, since=f"{since}s")
    if save_collection_output:
        with open(os.path.join(target_dir, "output.log"), "w") as _file:
            _file.write(output)
    return get_must_gather_output_dir(must_gather_path=target_dir)


def collect_ocp_gather(target_dir: str, since: str, save_collection_output: bool = True) -> str:
    output = run_must_gather(target_dir=target_dir, since=since)
    if save_collection_output:
        with open(os.path.join(target_dir, "output.log"), "w") as _file:
            _file.write(output)
    return get_must_gather_output_dir(must_gather_path=target_dir)
