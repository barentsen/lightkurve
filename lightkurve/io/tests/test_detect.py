import os
import tempfile

from astropy.io import fits

from ... import PACKAGEDIR, TessTargetPixelFile
from .. import detect_filetype


TESS_TPF = os.path.join(PACKAGEDIR, "tests", "data", "tess25155310-s01-first-cadences.fits.gz")


def test_detect_filetype():
    """Can we detect the correct filetype?"""
    k2_path = os.path.join(PACKAGEDIR, "tests", "data", "test-tpf-star.fits")
    assert detect_filetype(fits.open(k2_path)) == 'KeplerTargetPixelFile'
    assert detect_filetype(fits.open(TESS_TPF)) == 'TessTargetPixelFile'


def test_issue_775():
    """Regression test for #775."""
    tpf = TessTargetPixelFile(TESS_TPF)
    lc = tpf.to_lightcurve(aperture_mask='threshold')
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        lc.to_fits(path=temp.name)
        assert "TessLightCurve" in detect_filetype(fits.open(temp.name))
        os.unlink(tmp_name)
