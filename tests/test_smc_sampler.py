import pytest
import numpy as np
import pymc
from mpi4py import MPI
from smcpy.hdf5.hdf5_storage import HDF5Storage
from smcpy.particles.particle_chain import ParticleChain
from smc_tester import SMCTester

'''
Unit and regression tests for the smc_tester.
'''

arr_alm_eq = np.testing.assert_array_almost_equal

@pytest.fixture
def x_space():
    return np.arange(50)


@pytest.fixture
def error_std_dev():
    return 0.6


@pytest.fixture()
def smc_tester(request):
    np.random.seed(2)
    return SMCTester()


@pytest.fixture
def mpi_comm_world():
    return MPI.COMM_WORLD


@pytest.fixture
def cloned_comm():
    return MPI.COMM_WORLD.Clone()


def test_communicator_is_clone(smc_tester, mpi_comm_world):
    assert smc_tester._comm.__class__ is mpi_comm_world.__class__
    assert smc_tester._comm is not mpi_comm_world


def test_communicator_is_right_size(smc_tester, mpi_comm_world):
    assert smc_tester._size == mpi_comm_world.Get_size()


def test_communicator_is_right_rank(smc_tester, mpi_comm_world):
    assert smc_tester._rank == mpi_comm_world.Get_rank()


def test_setup_mcmc_sampler(smc_tester):
    from smcpy.mcmc.mcmc_sampler import MCMCSampler
    assert isinstance(smc_tester._mcmc, MCMCSampler)


@pytest.mark.parametrize("input_,exp_error", [(-1, ValueError),
                                              (0, ValueError),
                                              ('1', TypeError),
                                              (1.0, TypeError),
                                              (dict(), TypeError),
                                              ([1], TypeError)])
def test_pos_integer_input_checks(input_, exp_error, smc_tester):
    with pytest.raises(exp_error):
        smc_tester._check_num_particles(input_)
        smc_tester._set_temperature_schedule(input_)
        smc_tester._check_num_mcmc_steps(input_)


@pytest.mark.parametrize("input_,exp_error", [(-1, ValueError),
                                              ('1', TypeError),
                                              (dict(), TypeError),
                                              ([1], TypeError)])
def test_ess_threshold_input_checks(input_, exp_error, smc_tester):
    with pytest.raises(exp_error):
        smc_tester._check_ess_threshold(input_)


def test_ess_threshold_default_is_set(smc_tester):
    smc_tester.num_particles = 50
    ess_threshold = smc_tester._set_ess_threshold(None)
    expected = smc_tester.num_particles / 2.
    assert ess_threshold == expected


@pytest.mark.parametrize("input_,exp_error", [(1., TypeError),
                                              (['1'], TypeError),
                                              (dict(), TypeError)])
def test_autosave_file_input_checks(input_, exp_error, smc_tester):
    with pytest.raises(exp_error):
        smc_tester._check_autosave_file(input_)


@pytest.mark.parametrize("input_,expected", [('test.h5', HDF5Storage),
                                             (None, None.__class__)])
def test_autosave_behavior_is_set(input_, expected, smc_tester, cloned_comm):
    autosaver = smc_tester._set_autosave_behavior(input_)
    if cloned_comm.Get_rank() > 0:
        assert autosaver is None
    else:
        assert isinstance(autosaver, expected)
        smc_tester.cleanup_file(input_)


@pytest.mark.parametrize("prop_center,prop_scales,exp_error",
                         [(None, dict(), ValueError),
                          (1, dict(), TypeError),
                          (dict(), 1, TypeError),
                          (1, 1, TypeError)])
def test_check_set_proposal_distribution_inputs(prop_center, prop_scales,
                                                exp_error, smc_tester):
    with pytest.raises(exp_error):
        smc_tester._check_proposal_dist_inputs(prop_center, prop_scales)


@pytest.mark.parametrize("prop_center,prop_scales,exp_error",
                         [({'jabroni': 1}, {'a': 1, 'b': 2}, KeyError),
                          ({'a': 1, 'b': 2}, {'a': 1, 'jabroni': 2}, KeyError)])
def test_check_set_proposal_distribution_input_keys(prop_center, prop_scales,
                                                    exp_error, smc_tester):
    with pytest.raises(exp_error):
        smc_tester._check_proposal_dist_input_keys(prop_center, prop_scales)


@pytest.mark.parametrize("prop_center,prop_scales,exp_error",
                         [({'a': '1', 'b': 2}, {'a': 1., 'b': '2'}, TypeError),
                          ({'a': [1], 'b': 2}, {'a': 1, 'b': {}}, TypeError)])
def test_check_set_proposal_distribution_input_vals(prop_center, prop_scales,
                                                    exp_error, smc_tester):
    with pytest.raises(exp_error):
        smc_tester._check_proposal_dist_input_vals(prop_center, prop_scales)


def test_set_proposal_distribution_with_scales(smc_tester):
    smc_tester.when_proposal_dist_set_with_scales()
    assert smc_tester.proposal_center == smc_tester.expected_center
    assert smc_tester.proposal_scales == smc_tester.expected_scales


def test_set_proposal_distribution_no_scales(smc_tester):
    smc_tester.when_proposal_dist_set_with_no_scales()
    assert smc_tester.proposal_center == smc_tester.expected_center
    assert smc_tester.proposal_scales == smc_tester.expected_scales


@pytest.mark.parametrize("prop_center,expected", [(None, 1), (dict, 0)])
def test_set_start_time_based_on_proposal(smc_tester, prop_center, expected):
    smc_tester.proposal_center = prop_center
    smc_tester._set_start_time_based_on_proposal()
    assert smc_tester._start_time_step == expected


@pytest.mark.parametrize("params", [{'a': 2.42, 'b': 5.74},
                                    {'a': 2.3, 'b': 5.4},
                                    {'a': 2.43349633, 'b': 5.73716365}])
def test_likelihood_from_pymc(smc_tester, params, error_std_dev):
    std_dev = error_std_dev
    data = smc_tester._mcmc.data
    model_eval = smc_tester._mcmc.model.evaluate(params)
    smc_tester._mcmc.generate_pymc_model(fix_var=True, std_dev0=std_dev)
    log_like = smc_tester._evaluate_likelihood(params)
    calc_log_like = smc_tester.calc_log_like_manually(model_eval, data, std_dev)
    arr_alm_eq(log_like, calc_log_like)


def test_val_error_when_proposal_beyond_prior_support(smc_tester):
    with pytest.raises(ValueError):
        smc_tester.when_initial_particles_sampled_from_proposal_outside_prior()


def test_initialize_from_proposal(smc_tester, error_std_dev):
    params = {'a': np.array(2.43349633), 'b': np.array(5.73716365)}
    weight = 0.06836560508406836
    log_like = -706.453419056

    smc_tester.when_initial_particles_sampled_from_proposal(error_std_dev)

    first_particle = smc_tester.particles[0]
    first_particle.print_particle_info()
    arr_alm_eq(first_particle.params.values(), params.values())
    arr_alm_eq(first_particle.weight, weight)
    arr_alm_eq(first_particle.log_like, log_like)
    assert len(smc_tester.particles) == 1


def test_initialize_from_prior(smc_tester, error_std_dev):
    params = {'a': np.array(-1.87449914), 'b': np.array(-9.45595268)}
    weight = 0.0
    log_like = -1242179.09405

    error_std_dev = 0.6
    smc_tester.when_initial_particles_sampled_from_prior(error_std_dev)

    first_particle = smc_tester.particles[0]
    first_particle.print_particle_info()
    arr_alm_eq(first_particle.params.values(), params.values())
    arr_alm_eq(first_particle.weight, weight)
    arr_alm_eq(first_particle.log_like, log_like)
    assert len(smc_tester.particles) == 1


def test_initialize_particle_chain(smc_tester, cloned_comm):
    error_std_dev = 0.6

    smc_tester.when_initial_particles_sampled_from_proposal(error_std_dev)
    particle_chain = smc_tester._initialize_particle_chain(smc_tester.particles)
    if cloned_comm.Get_rank() == 0:
        assert isinstance(particle_chain, ParticleChain)
        assert len(particle_chain.get_particles()) == cloned_comm.Get_size()
        assert particle_chain.get_num_steps() == 1
        arr_alm_eq(sum(particle_chain.get_weights()), 1.)
    else:
        assert particle_chain is None


@pytest.mark.parametrize("restart_step", [-1, 3])
def test_raise_value_error_when_restart_step_invalid(smc_tester, restart_step):
    with pytest.raises(ValueError):
        smc_tester.when_sampling(restart_step, hdf5_to_load=None,
                                 autosave_file=None)


def test_load_save_particle_chain(smc_tester):
    pass