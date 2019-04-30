import pytest
import numpy as np
from smcpy.smc.smc_step import SMCStep
from smcpy.particles.particle import Particle

arr_alm_eq = np.testing.assert_array_almost_equal


@pytest.fixture
def particle():
    particle = Particle({'a': 1, 'b': 2}, 0.2, -0.2)
    return particle


@pytest.fixture
def particle_list():
    particle = Particle({'a': 1, 'b': 2}, 0.2, -0.2)
    return [particle.copy() for i in range(5)]


@pytest.fixture
def mixed_particle_list():
    particle_1 = Particle({'a': 1, 'b': 2}, -0.2, -0.2)
    particle_2 = Particle({'a': 2, 'b': 4}, -0.2, -0.2)
    list_1 = [particle_1.copy() for i in range(3)]
    list_2 = [particle_2.copy() for i in range(2)]
    return list_1 + list_2


@pytest.fixture
def linear_particle_list():
    a = np.arange(0, 20)
    b = [2 * val + np.random.normal(0, 1) for val in a]
    w = 0.1
    p_list = [Particle({'a': a[i], 'b': b[i]}, w, -.2) for i in a]
    return p_list


@pytest.fixture
def mixed_weight_particle_list():
    p_list = [Particle({'a': 1, 'b': 2}, i, -.2) for i in np.arange(.1, .5, .1)]
    return p_list


@pytest.fixture
def step_tester():
    return SMCStep()


@pytest.fixture
def filled_step(step_tester, particle_list):
    step_tester.set_particles(particle_list)
    return step_tester


@pytest.fixture
def mixed_step(step_tester, mixed_particle_list):
    step_tester.set_particles(mixed_particle_list)
    return step_tester


@pytest.fixture
def linear_step(step_tester, linear_particle_list):
    step_tester.set_particles(linear_particle_list)
    return step_tester


@pytest.fixture
def mixed_weight_step(step_tester, mixed_weight_particle_list):
    step_tester.set_particles(mixed_weight_particle_list)
    return step_tester


def test_add_particle(filled_step, particle):
    orig_num_particles = len(filled_step.particles)
    filled_step.add_particle(particle)
    assert len(filled_step.particles) == orig_num_particles + 1


def test_copy_step(filled_step):
    filled_step_copy = filled_step.copy()
    filled_step_copy.particles == []
    assert filled_step.particles != []


def test_type_error_when_particle_not_list(step_tester):
    with pytest.raises(TypeError):
        step_tester.set_particles("Bad param type")


def test_type_error_not_particle_class(step_tester):
    with pytest.raises(TypeError):
        step_tester.set_particles([1, 2, 3])


def test_private_variable_creation(step_tester, particle_list):
    step_tester.set_particles(particle_list)
    assert step_tester.particles == particle_list


def test_get_likes(filled_step):
    assert np.array_equal(filled_step.get_likes(),
                          [pytest.approx(0.818730753078)] * 5)


def test_get_log_likes(filled_step):
    assert np.array_equal(filled_step.get_log_likes(), [-0.2] * 5)


def test_get_mean(filled_step):
    assert filled_step.get_mean()['a'] == 1.0


def test_get_log_weights(filled_step):
    assert np.array_equal(filled_step.get_log_weights(), [0.2] * 5)


def test_calcuate_covariance_not_positive_definite(filled_step):
    assert np.array_equal(filled_step.calculate_covariance(),
                          np.eye(2))


def test_calculate_covariance(linear_step):
    a = linear_step.get_params('a')
    b = linear_step.get_params('b')
    exp_cov = np.cov(a, b)
    arr_alm_eq(linear_step.calculate_covariance(), exp_cov)


def test_normalize_step_log_weights(mixed_weight_step):
    mixed_weight_step.normalize_step_log_weights()
    for index, p in enumerate(mixed_weight_step.particles):
        p.log_weight = np.exp(p.log_weight)
    assert sum(mixed_weight_step.get_log_weights()) == 1


def test_normalize_step_weights(mixed_weight_step):
    normalized_weights = mixed_weight_step.normalize_step_weights()
    assert sum(normalized_weights) == 1


def test_compute_ess(filled_step):
    assert filled_step.compute_ess() == pytest.approx(5.0)


def test_get_params(filled_step):
    assert np.array_equal(filled_step.get_params('a'), np.array(5 * [1]))


def test_get_param_dicts(filled_step):
    assert filled_step.get_param_dicts() == 5 * [{'a': 1, 'b': 2}]


def test_resample(mixed_step):
    np.random.seed(1)
    prior_particle = mixed_step.particles
    mixed_step.resample()
    assert mixed_step.particles != prior_particle


def test_resample_uniform(mixed_step):
    mixed_step.resample()
    log_weights = mixed_step.get_log_weights()
    np.testing.assert_almost_equal(max(log_weights) - min(log_weights), 0)


def test_print_particle_info(filled_step, capfd):
    filled_step.print_particle_info(3)
    out, err = capfd.readouterr()
    assert "params = {'a': 1, 'b': 2}" in out
