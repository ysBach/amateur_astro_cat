import re
import urllib.request
from pathlib import Path
from time import sleep

import astroplan as ap
import numpy as np
import pandas as pd
import requests
from astropy import units as u
from astropy.wcs import WCS
from astroquery.skyview import SkyView
from bs4 import BeautifulSoup
from matplotlib import pyplot as plt
from matplotlib import rcParams
from photutils import SkyRectangularAperture
import ysvisutilpy as yvu

plt.style.use('default')
rcParams.update({
    'font.family': 'Monospace', 'font.size': 10, 'mathtext.fontset': 'stix',
    'axes.formatter.use_mathtext': True, 'axes.formatter.limits': (-4, 4),
    'axes.grid': True, 'grid.color': 'gray', 'grid.linewidth': 0.5,
    'xtick.top': True, 'ytick.right': True,
    'xtick.direction': 'inout', 'ytick.direction': 'inout',
    'xtick.minor.size': 2.0, 'ytick.minor.size': 2.0,  # default 2.0
    'xtick.major.size': 4.0, 'ytick.major.size': 4.0,  # default 3.5
    'xtick.minor.visible': True, 'ytick.minor.visible': True
})


# Directory to save image files
SAVEDIR = Path("figs/")
SAVEDIR.mkdir(exist_ok=True)


def save_finder_plot(savepath, longname, obj_coord, plotkw={}):
    if savepath.exists():
        return
    hdu = SkyView.get_images(_coo.coord, survey='DSS', width=35*u.arcmin, height=35*u.arcmin,
                             coordinates="ICRS", projection="Tan", pixels=200, scaling="Linear",
                             sampler="NN", resolver=None, deedger=None, lut=None, grid=None, gridlabels=None,
                             radius=None, cache=True, show_progress=True)[0][0]
    wcs = WCS(hdu.header)
    fov = SkyRectangularAperture(obj_coord, w=21*u.arcmin, h=21*u.arcmin).to_pixel(wcs)

    fig = plt.figure(figsize=(3.5, 3.5))
    ax = plt.subplot(projection=wcs)
    yvu.norm_imshow(ax, hdu.data, **plotkw)
    ax.set_xlabel(r"$\longleftarrow \mathrm{RA}\ (\alpha)$", fontsize=12)
    ax.set_ylabel(r"$\mathrm{DEC}\ (\delta) \longrightarrow$", fontsize=12)
    ax.set_title(longname)

    fov.plot(ax, color='red')
    ax.text(0.2, 0.15, "21'×21'", transform=ax.transAxes,
            fontsize=12, fontfamily="monospace", fontweight="bold", color="r")
    ax.tick_params(direction="out", fontfamily="monospace")
    ax.coords[0].set_axislabel(r"$\longleftarrow \mathrm{RA}\ (\alpha)$", minpad=0.5, fontsize=12)
    ax.coords[1].set_axislabel(r"$\mathrm{DEC}\ (\delta) \longrightarrow$", minpad=0.5, fontsize=12)

    # plt.tight_layout()
    plt.savefig(savepath, bbox_inches="tight")
    plt.cla()
    plt.close()
    return


# %%
# ********************************************************************************************************** #
# *                                         QUERY RA/DEC OF OBJECTS                                        * #
# ********************************************************************************************************** #
cat = pd.read_csv(Path(__file__).parent/"amastro_catalog.csv", delimiter=',')
coo = []
# Once it is done, the info will be cached to the astropy cache directory.
# You may clean it by astropy.utils.clear_download_cache()
# See https://docs.astropy.org/en/stable/utils/index.html
for _, row in cat.iterrows():
    catid = row['ID']
    othid = row["Other ID"]
    name = row["Name"]
    typekey = row["Type"]
    if not isinstance(othid, float):  # if it was a float, it means it was a NaN.
        othid = othid.split(" & ")[0]

    try:
        _coo = ap.FixedTarget.from_name(catid)
    except:  # whatever Error occurs...
        _coo = ap.FixedTarget.from_name(othid)
    _coo.name = catid + f"({row['Type']})"
    coo.append(_coo)

    longname = f"{catid} ({othid}, {typekey})"
    longname += f"\n{name}" if isinstance(name, str) else ""
    save_finder_plot(SAVEDIR/f"DSS-200px-{catid}.jpg",
                     longname, _coo.coord, plotkw={"origin": "lower", "cmap": "viridis", "zscale": False})
    save_finder_plot(SAVEDIR/f"DSS-200px-{catid}-zscale.jpg",
                     longname, _coo.coord, plotkw={"origin": "lower", "cmap": "viridis", "zscale": True})


coo = np.array(coo)
cat["RA"] = [float(f"{_coo.ra.deg:.4f}") for _coo in coo]
cat["DEC"] = [float(f"{_coo.dec.deg:.4f}") for _coo in coo]
cat.to_csv(Path(__file__).parent/"amastro_catalog_radec.csv", index=False)

# %%


# style_kwargs = dict(cmap="viridis")
# aplt.plot_finder_image(coo[31], fov_radius=30*u.arcmin, grid=True, style_kwargs=style_kwargs, log=True)

# %%
# ********************************************************************************************************** #
# *                              DOWNLOAD THUMBNAIL IMAGES FROM WIKI : MESSIER                             * #
# ********************************************************************************************************** #
url_base = "https://en.wikipedia.org/"

url_main = url_base + "wiki/Messier_object"
r = requests.get(url_main)
soup = BeautifulSoup(r.text, 'html.parser')
table = soup.find_all(class_='wikitable')[0]
imgs = table.find_all(class_="image")

for i, img in enumerate(imgs):
    savepath = SAVEDIR/f"Messier_{i+1:03d}.jpg"
    if savepath.exists():
        continue
    imgstr = str(img)
    imgurl = "https:" + re.split(r"src=", str(imgstr))[1][1:].split('"')[0]
    print(imgurl)
    urllib.request.urlretrieve(imgurl, savepath)
    sleep(0.8)

# %%
# ********************************************************************************************************** #
# *                              DOWNLOAD THUMBNAIL IMAGES FROM WIKI : Caldwell                            * #
# ********************************************************************************************************** #
url_main = url_base + "wiki/Caldwell_catalogue"
r = requests.get(url_main)
soup = BeautifulSoup(r.text, 'html.parser')
table = soup.find_all(class_='wikitable')[1]
imgs = table.find_all(class_="image")

for i, img in enumerate(imgs):
    savepath = SAVEDIR/f"Caldwell_{i+1:03d}.jpg"
    if savepath.exists():
        continue
    imgstr = str(img)
    imgurl = "https:" + re.split(r"src=", str(imgstr))[1][1:].split('"')[0]
    print(imgurl)
    urllib.request.urlretrieve(imgurl, savepath)
    sleep(0.8)
