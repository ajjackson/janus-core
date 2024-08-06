"""Test equation of state calculations."""

from pathlib import Path

from ase.eos import EquationOfState
from ase.io import read
import pytest

from janus_core.calculations.eos import EoS
from janus_core.calculations.single_point import SinglePoint
from janus_core.helpers.mlip_calculators import choose_calculator
from tests.utils import assert_log_contains

DATA_PATH = Path(__file__).parent / "data"
MODEL_PATH = Path(__file__).parent / "models" / "mace_mp_small.model"


def test_calc_eos(tmp_path):
    """Test calculating equation of state from ASE atoms object."""
    struct = read(DATA_PATH / "NaCl.cif")
    log_file = tmp_path / "eos.log"
    struct.calc = choose_calculator(architecture="mace_mp", model=MODEL_PATH)

    eos = EoS(
        struct,
        file_prefix=tmp_path / "NaCl",
        log_kwargs={"filename": log_file},
    )
    results = eos.run()
    assert all(key in results for key in ("eos", "bulk_modulus", "e_0", "v_0"))

    # Check geometry optimization run by default
    assert_log_contains(
        log_file,
        includes=["Using filter", "Using optimizer", "Starting geometry optimization"],
    )


def test_no_optimize(tmp_path):
    """Test not optimizing structure before calculation."""
    log_file = tmp_path / "eos.log"
    single_point = SinglePoint(
        struct_path=DATA_PATH / "NaCl.cif",
        architecture="mace",
        calc_kwargs={"model": MODEL_PATH},
    )
    eos = EoS(
        single_point.struct,
        minimize=False,
        file_prefix=tmp_path / "NaCl",
        log_kwargs={"filename": log_file},
    )
    eos.run()

    # Check geometry optimization turned off
    assert_log_contains(
        log_file,
        excludes=["Using filter", "Using optimizer", "Starting geometry optimization"],
    )


test_data_potentials = [("m3gnet", "cpu"), ("chgnet", "cpu")]


@pytest.mark.parametrize("arch, device", test_data_potentials)
def test_extra_potentials(arch, device, tmp_path):
    """Test m3gnet and chgnet potentials."""
    log_file = tmp_path / "eos.log"
    eos_fit_path = tmp_path / "NaCl-eos-fit.dat"

    single_point = SinglePoint(
        struct_path=DATA_PATH / "NaCl.cif",
        architecture=arch,
        device=device,
    )

    eos = EoS(
        single_point.struct,
        minimize=False,
        file_prefix=tmp_path / "NaCl",
        log_kwargs={"filename": log_file},
    )
    results = eos.run()

    assert isinstance(results["eos"], EquationOfState)

    # Check contents of EoS fit data file
    with open(eos_fit_path, encoding="utf8") as eos_fit_file:
        lines = eos_fit_file.readlines()

    assert len(lines) == 2
    assert len(lines[1].split()) == 3


def test_invalid_struct():
    """Test setting invalid structure."""
    single_point = SinglePoint(
        struct_path=DATA_PATH / "benzene-traj.xyz",
        architecture="mace_mp",
        calc_kwargs={"model": MODEL_PATH},
    )

    with pytest.raises(NotImplementedError):
        EoS(
            single_point.struct,
        )
    with pytest.raises(ValueError):
        EoS(
            "structure",
        )
