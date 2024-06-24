import pytest
from time import sleep

from coherent_lasers import GenesisMXVoxelLaser

LASER1 = {
    "id": "test_laser",
    "conn": "A700467EP203"
}

LASER2 = {
    "id": "test_laser2",
    "conn": "J687424BP914"
}


@pytest.fixture
def laser1():
    laser = GenesisMXVoxelLaser(**LASER1)
    yield laser
    laser.disable()


@pytest.fixture
def laser2():
    laser = GenesisMXVoxelLaser(**LASER2)
    yield laser
    laser.disable()


def test_power_mw(laser1):
    laser1.power_setpoint_mw = 100.0
    assert laser1.power_setpoint_mw == pytest.approx(100.0, rel=1e-2)
    sleep(1)
    assert laser1.power_mw == pytest.approx(100.0, rel=1e-2)


def test_disable(laser1, laser2):
    laser1.power_setpoint_mw, laser2.power_setpoint_mw = 500.0, 500.0
    # disable 1 laser and check difference
    laser1.disable()
    sleep(1)
    assert laser1.power_mw == pytest.approx(0.0, rel=1e-2)
    assert laser2.power_mw == pytest.approx(500.0, rel=1e-2)
    laser2.disable()
    sleep(1)
    assert laser2.power_mw == pytest.approx(0.0, rel=1e-2)
    laser1.enable()
    laser2.enable()
