"""Test the features of the lightkurve.prf.scenemodels module."""
from __future__ import division, print_function

import os

from astropy.io import fits
import numpy as np
from numpy.testing import assert_allclose
from scipy.stats import mode

from ... import PACKAGEDIR
from ...prf import FixedValuePrior, GaussianPrior, UniformPrior
from ...prf import StarPrior, BackgroundPrior, FocusPrior, MotionPrior
from ...prf import SceneModel, PRFPhotometry
from ...prf import SimpleKeplerPRF, KeplerPRF


def test_fixedvalueprior():
    fvp = FixedValuePrior(1.5)
    assert fvp.mean == 1.5
    assert fvp(1.5) == 0


def test_starprior():
    """Tests the StarPrior class."""
    col, row, flux = 1, 2, 3
    sp = StarPrior(col=GaussianPrior(mean=col, var=0.1),
                   row=GaussianPrior(mean=row, var=0.1),
                   flux=GaussianPrior(mean=flux, var=0.1))
    assert sp.col.mean == col
    assert sp.row.mean == row
    assert sp.flux.mean == flux
    assert sp.evaluate(col, row, flux) == 0
    # The object should be callable
    assert sp(col, row, flux + 0.1) == sp.evaluate(col, row, flux + 0.1)
    # A point further away from the mean should have a larger negative log likelihood
    assert sp.evaluate(col, row, flux) < sp.evaluate(col, row, flux + 0.1)
    # Object should have a nice __repr__
    assert 'StarPrior' in str(sp)


def test_backgroundprior():
    """Tests the BackgroundPrior class."""
    flux = 2.
    bp = BackgroundPrior(flux=flux)
    assert bp.flux.mean == flux
    assert bp(flux) == 0.
    assert not np.isfinite(bp(flux + 0.1))


def test_scene_model_simple():
    prf = SimpleKeplerPRF(channel=16, shape=[10, 10], column=15, row=15)
    scene = SceneModel(prfmodel=prf)
    assert scene.prfmodel.channel == 16


def test_scene_model():
    col, row, flux, bgflux = 1, 2, 3, 4
    shape = (7, 8)
    model = SceneModel(star_priors=[StarPrior(col=GaussianPrior(mean=col, var=2**2),
                                              row=GaussianPrior(mean=row, var=2**2),
                                              flux=UniformPrior(lb=flux - 0.5, ub=flux + 0.5),
                                              targetid="TESTSTAR")],
                       background_prior=BackgroundPrior(flux=GaussianPrior(mean=bgflux, var=bgflux)),
                       focus_prior=FocusPrior(scale_col=GaussianPrior(mean=1, var=0.0001),
                                              scale_row=GaussianPrior(mean=1, var=0.0001),
                                              rotation_angle=UniformPrior(lb=-3.1415, ub=3.1415)),
                       motion_prior=MotionPrior(shift_col=GaussianPrior(mean=0., var=0.01),
                                                shift_row=GaussianPrior(mean=0., var=0.01)),
                       prfmodel=KeplerPRF(channel=40, shape=shape, column=30, row=20),
                       fit_background=True,
                       fit_focus=False,
                       fit_motion=False)
    # Sanity checks
    assert model.star_priors[0].col.mean == col
    assert model.star_priors[0].targetid == 'TESTSTAR'
    # Test initial guesses
    params = model.get_initial_guesses()
    assert params.stars[0].col == col
    assert params.stars[0].row == row
    assert params.stars[0].flux == flux
    assert params.background.flux == bgflux
    assert len(params.to_array()) == 4  # The model has 4 free parameters
    assert_allclose([col, row, flux, bgflux], params.to_array(), rtol=1e-5)
    # Predict should return an image
    assert model.predict().shape == shape
    # Test __repr__
    assert 'TESTSTAR' in str(model)


def test_prf_vs_aperture_photometry():
    # Is the PRF photometry result consistent with simple aperture photometry?
    tpf_fn = os.path.join(PACKAGEDIR, "tests", "data", "ktwo201907706-c01-first-cadence.fits.gz")
    tpf = fits.open(tpf_fn)
    col, row = 173, 526
    fluxsum = np.sum(tpf[1].data)
    bkg = mode(tpf[1].data, None)[0]
    prfmodel = KeplerPRF(channel=tpf[0].header['CHANNEL'],
                         column=col, row=row,
                         shape=tpf[1].data.shape)
    star_priors = [StarPrior(col=UniformPrior(lb=prfmodel.col_coord[0], ub=prfmodel.col_coord[-1]),
                             row=UniformPrior(lb=prfmodel.row_coord[0], ub=prfmodel.row_coord[-1]),
                             flux=UniformPrior(lb=0.5*fluxsum, ub=1.5*fluxsum))]
    background_prior = BackgroundPrior(flux=UniformPrior(lb=.5*bkg, ub=1.5*bkg))
    scene = SceneModel(star_priors=star_priors,
                       background_prior=background_prior,
                       prfmodel=prfmodel)
    #fluxo, colo, rowo, _ = scene.get_initial_guesses()
    #data=tpf[1].data, ref_col=prf.col_coord[0], ref_row=prf.row_coord[0])
    #prior = JointPrior(UniformPrior(lb=0.1*fluxo, ub=fluxo),
    #                   UniformPrior(lb=prf.col_coord[0], ub=prf.col_coord[-1]),
    #                   UniformPrior(lb=prf.row_coord[0], ub=prf.row_coord[-1]),
    #                   GaussianPrior(mean=1, var=1e-2),
    #                   GaussianPrior(mean=1, var=1e-2),
    #                   GaussianPrior(mean=0, var=1e-2),
    #                   UniformPrior(lb=bkg - .5*bkg, ub=bkg + .5*bkg))
    #logL = PoissonPosterior(tpf[1].data, mean=scene, prior=prior)
    #result = logL.fit(x0=prior.mean, method='powell')
    #prf_flux, prf_col, prf_row, prf_scale_col, prf_scale_row, prf_rotation, prf_bkg = logL.opt_result.x
    #assert result.success is True
    #assert np.isclose(prf_col, colo, rtol=1e-1)
    #assert np.isclose(prf_row, rowo, rtol=1e-1)
    #assert np.isclose(prf_bkg, np.percentile(tpf[1].data, 10), rtol=0.1)

    #phot = PRFPhotometry(scene)
    #phot.run(tpf[1].data)

    result = scene.fit(tpf[1].data)
    #assert np.isclose(result.stars[0].flux, fluxsum, rtol=0.1)
    #assert np.isclose(opt_params[1], prf_col, rtol=1e-1)
    #assert np.isclose(opt_params[2], prf_row, rtol=1e-1)
    #assert np.isclose(opt_params[-1], prf_bkg, rtol=0.1)

    """
    # Test KeplerPRFPhotometry class
    kepler_phot = PRFPhotometry(scene_model=scene, prior=prior)
    tpf_flux = tpf[1].data.reshape((1, tpf[1].data.shape[0], tpf[1].data.shape[1]))
    kepler_phot.fit(tpf_flux=tpf_flux)
    opt_params = kepler_phot.opt_params.reshape(-1)
    assert np.isclose(opt_params[0], prf_flux, rtol=0.1)
    assert np.isclose(opt_params[1], prf_col, rtol=1e-1)
    assert np.isclose(opt_params[2], prf_row, rtol=1e-1)
    assert np.isclose(opt_params[-1], prf_bkg, rtol=0.1)
    """
