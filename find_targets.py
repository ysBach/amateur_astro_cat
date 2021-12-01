# %%
import argparse
import datetime
from pathlib import Path

import astroplan as ap
import astropy.units as u
import numpy as np
import pandas as pd
import pytz
from astroplan import plots as aplt
from astropy.coordinates import EarthLocation, get_body, SkyCoord
from astropy.time import Time
from matplotlib import pyplot as plt
from matplotlib import rcParams
import warnings
warnings.filterwarnings('ignore', append=True)

try:
    from rich import print
    from rich.traceback import install
    install()
except ImportError:
    print("You may want to install `rich` by $ pip install rich")
    pass


plt.style.use('default')
rcParams.update({
    'font.family': 'Times', 'font.size': 12, 'mathtext.fontset': 'stix',
    'axes.formatter.use_mathtext': True, 'axes.formatter.limits': (-4, 4),
    'axes.grid': True, 'grid.color': 'gray', 'grid.linewidth': 0.5,
    'xtick.top': True, 'ytick.right': True,
    'xtick.direction': 'inout', 'ytick.direction': 'inout',
    'xtick.minor.size': 4.0, 'ytick.minor.size': 4.0,  # default 2.0
    'xtick.major.size': 8.0, 'ytick.major.size': 8.0,  # default 3.5
    'xtick.minor.visible': True, 'ytick.minor.visible': True
})

PLANETS = {
    'Mercury': "gray",
    'Venus': "brown",
    'Mars': "red",
    'Jupiter': "orange",
    'Saturn': "olive",
    'Uranus': "lightseagreen",
    'Neptune': "blue"
}

COLS2DROP = ["Other ID", "Distance (kly)", "Constellation", "RA", "DEC"]

PLOTKW = {
    'gal': dict(ls="-", alpha=0.7, lw=2),
    'Neb': dict(ls="--", alpha=1, lw=2),
    "cl": dict(ls="-.", alpha=1, lw=2),
}
PLOTKW_OTHERS = dict(ls=":", alpha=1, lw=2)

INFOSTR = """
Abbreviations for "Type" column
* cl: Cluster
  - cl-O: open cluster
  - cl-G: globular cluster
* gal: Galaxy
  - gal-SB: Barred spiral galaxy
  - gal-S: Spiral galaxy
  - gal-S0: Lenticular galaxy
  - gal-E: Elliptical galaxy
  - gal-dE: Dwarf elliptical galaxy
  - gal-dSph: Dwarf Spheroidal Galaxy
  - gal-cD: Supergiant Elliptical Galaxy
  - gal-Irr: Irregular galaxy
  - gal-IrrB: Barred irregular galaxy
  - gal-Inter: Interacting galaxy
* Neb: Nebula
  - Neb-P: Planetary nebula
  - Neb-HII: H II Region Nebula
  - Neb-SN: Supernova remnant
* MW: Milky Way

Original of Messier data from https://en.wikipedia.org/wiki/Messier_object
Original of Caldwell data from https://en.wikipedia.org/wiki/Caldwell_catalogue
"""

p = argparse.ArgumentParser(description='')

# TODO: let user choose which to use first y-axis (airmass, altitude)
p.add_argument("YYYY", nargs='?', type=int,
               help="Year; If not given, current time is used")
p.add_argument("MM", nargs='?', default=1, type=int,
               help="Month   (1 <= month <= 12)")
p.add_argument("DD", nargs='?', default=1, type=int,
               help="Date    (1 <= day <= number of days in the given month and year)")
p.add_argument("HH", nargs='?', default=0, type=int,
               help="Hour    (0 <= hour < 24)")
p.add_argument("mm", nargs='?', default=0, type=int,
               help="Minutes (0 <= minute < 60)")
p.add_argument("ss", nargs='?', default=0, type=int,
               help="Seconds (0 <= second < 60)")

p.add_argument("-U", "--UTC", action="store_true",
               help="Time is in UTC instead of local time")
p.add_argument("-M", "--Messier", action="store_false",
               help="Do NOT use Messier objects")
p.add_argument("-C", "--Caldwell", action="store_false",
               help="Do NOT use Caldwell objects")
p.add_argument("-X", "--airmass", action="store_true",
               help="Whether to use the primary y-axis as airmass (`X`)")
p.add_argument("-A", "--always-visible", action="store_true",
               help="Discard objects that are not *always* visible during the timespan?")
p.add_argument("-N", "--nickname", action="store_true",
               help="Use only those that have common nick name.")
p.add_argument("-E", "--type-exclude", action="store_true",
               help="Whether the -T (--types) is for exclusion")

p.add_argument("-c", "--currentlocation", action="store_true",
               help=("Use current location and timezone automatically "
                     + "(using http://ip-api.com/json/)"))
p.add_argument("-v", "--verbose", action="store_true",
               help="Print miscellaneous information")

p.add_argument("-d", "--duration", default=2., type=float,
               help="Duration of the observing run (+- this number) [hour]")
p.add_argument("-l", "--location", nargs=2, default=[127, 37.5],
               help="(longitude, latitude) [˚]; Used in astropy.coordinates.EarthLocation")
p.add_argument("-z", "--timezone", default="Asia/Seoul", type=str,
               help="Time zone")

p.add_argument("-a", "--min-alt", default=30., type=float,
               help="Minimum altitude of the object to be drawn [deg]")
p.add_argument("-p", "--min-alt-pl", default=25., type=float,
               help="Minimum altitude of the planetary objects to be drawn [deg]")
p.add_argument("-T", "--types", default=None, nargs='+',
               help="Target types to be drawn or excluded (exclusion by -E)")
p.add_argument("-t", "--targets", nargs='+', default=None,
               help="Target names to be drawn")
p.add_argument("-o", "--output", default=None, help="HTML name to save DataFrame")

args = p.parse_args()


def check_observable(min_alt, observer, targets, times, always):
    consts = [ap.AltitudeConstraint(min_alt*u.deg)]
    # , ap.AtNightConstraint(max_solar_altitude=0*u.deg)
    mask_fun = ap.is_always_observable if always else ap.is_observable
    mask = mask_fun(
        constraints=consts,
        observer=observer,
        targets=targets.tolist(),
        times=times
    )
    # coo_up = []
    # for _m, _t in zip(mask, targets):
    #     if _m:
    #         coo_up.append(_t)
    return mask


def get_geoloc(use_current_location, verbose):
    ''' Find geological location information from ip-api.com (lon, lat, timezone).
    '''
    if use_current_location:
        # TODO: Save these as cache files
        from requests import get
        ip = get('https://api.ipify.org').content.decode('utf8')
        response = get("http://ip-api.com/json/" + ip).json()
        # {'status': 'success', 'country': 'South Korea', 'countryCode': 'KR',
        # 'region': '11', 'regionName': 'Seoul', 'city': 'Gwanak-gu', 'zip': '08841',
        # 'lat': 37.4625, 'lon': 126.9438, 'timezone': 'Asia/Seoul', 'isp': 'SNU',
        # 'org': '', 'as': 'AS9488 Seoul National University', 'query': '147.46.135.73'}
        lon = float(response['lon'])*u.deg
        lat = float(response['lat'])*u.deg
        tz = pytz.timezone(response['timezone'])
        if verbose:
            print(response)
    else:
        lon = float(args.location[0])*u.deg
        lat = float(args.location[1])*u.deg
        tz = pytz.timezone(args.timezone)
    return lon, lat, tz


def get_time(YYYY, MM, DD, HH, mm, ss, in_utc, tz):
    ''' Parse the time infromation
    '''
    if YYYY is None:
        _obstime = datetime.datetime.utcnow()
        _localnow = datetime.datetime.now()
        args.YYYY = _localnow.year
        args.MM = _localnow.month
        args.DD = _localnow.day
        args.HH = _localnow.hour
        args.mm = _localnow.minute
    else:
        YYYY = int(YYYY)
        MM = int(MM)
        DD = int(DD)
        HH = int(HH)
        mm = int(mm)
        ss = int(ss)
        if in_utc:
            _obstime = datetime.datetime(YYYY, MM, DD, HH, mm, ss)
        else:
            _obstime = datetime.datetime(YYYY, MM, DD, HH, mm, ss).astimezone(tz)
    return _obstime


def add2kw(kw, cat, coo, mask, cmap):
    count = np.sum(mask)
    kw["df"] = cat[mask]
    kw["coo"] = coo[mask]
    kw["colors"] = cmap(np.linspace(0, 1, count))


def parseID(catid):
    if catid.startswith("M"):
        catname = "Messier"
    elif catid.startswith("C"):
        catname = "Caldwell"
    else:
        catname = None
    return catname


def mk_wikilink(catid):
    catname = parseID(catid)
    url = f"https://en.wikipedia.org/wiki/{catname}_{catid[1:]}"
    return f'<p style="font-size:large"><a href="{url}" title="Link">{catid:s}</a></p>'


def alt_color(alt):
    altval = float(alt)
    if altval < 0:
        color = "red"
    elif altval < args.min_alt:
        color = "orange"
    else:
        color = "limegreen"

    return f'<p style="color:{color}">{alt:.1f}˚</p>'


if __name__ == "__main__":
    if args.verbose:
        print(args)

    TOP = Path(__file__).parent
    OUTPUT = Path(args.output).absolute() if args.output else Path("output.html").absolute()
    FIGDIR = (TOP/"figs").relative_to(OUTPUT.parent)

    # == Get location and time information =============================================== #
    lon, lat, tz = get_geoloc(args.currentlocation, args.verbose)
    _obstime = get_time(args.YYYY, args.MM, args.DD,
                        args.HH, args.mm, args.ss,
                        args.UTC, tz)

    print(f"Date & Time : {_obstime} ({tz})")
    print(f"lon , lat  : {lon.value:.2f}˚, {lat.value:.2f}˚")

    OBSTIME = Time(_obstime)  # in UTC
    dt = args.duration*u.hour
    OBSTIME_RANGE = Time([OBSTIME - dt, OBSTIME, OBSTIME + dt])
    OBSTIMES = OBSTIME + np.linspace(-dt, dt, max(6, int(args.duration*12)))
    # around once per 5 minutes

    # NOTE: Default elevation of the observatory is set to 500m. Only small
    #   offset will be added, and that is insignificant for the purpose (maybe
    #   about the size of line width...).
    loc = EarthLocation.from_geodetic(lon, lat, 500*u.m)
    obs = ap.Observer(location=loc, timezone=tz)

    # == Prepare catalog ================================================================= #
    cat = pd.read_csv(TOP/"amastro_catalog_radec.csv", delimiter=',', comment="#")
    if args.targets is not None:
        cat = cat[cat["ID"].isin(args.targets)]
        if args.verbose:
            print(f"Choosing only thses: {args.targets}")
    else:
        if not args.Messier:
            if args.verbose:
                print("Messier objects are ignored.")
            cat = cat[~cat["ID"].str.startswith("M")]
        if not args.Caldwell:
            if args.verbose:
                print("Caldwell objects are ignored.")
            cat = cat[~cat["ID"].str.startswith("C")]
        if args.types is not None:
            if args.type_exclude:
                cat = cat[~cat["Type"].isin(args.types)]
                if args.verbose:
                    print(f"Following types will be ignored: {args.types}")
            else:
                cat = cat[cat["Type"].isin(args.types)]
                if args.verbose:
                    print(f"Only take the following types: {args.types}")

        if args.nickname:
            if args.verbose:
                print("Only those with common nicknames are selected.")
            cat = cat[cat["Name"].notna()]

    if args.verbose:
        print(f"{len(cat)} objects are selected by the user.")

    cat.sort_values(by="DEC", ascending=False, ignore_index=True, inplace=True)

    # plotting order will anyway be based on Type.
    coo = np.array(
        [ap.FixedTarget(SkyCoord(ra=_a*u.deg, dec=_d*u.deg), name=f"{_id} ({_t})")
         for _a, _d, _id, _t in zip(cat["RA"], cat["DEC"], cat["ID"], cat["Type"])]
    )

    # == Find coordinates of planets ===================================================== #
    coo_pl = []
    for planet in PLANETS.keys():
        _coo = get_body(planet, time=OBSTIME, location=loc)
        _coo.name = planet
        coo_pl.append(_coo)
    # RA/DEC only at the middle of the time.
    coo_pl = np.array(coo_pl)

    # style_ini = dict(style_kwargs=dict(marker=".", color="r"))
    # style_mid = dict(style_kwargs=dict(marker="x", color="r"))
    # style_end = dict(style_kwargs=dict(marker="o", color="r"))
    # OBSTIMES_5 = OBSTIME + np.linspace(-1, 1, 5)*u.hour
    # aplt.plot_sky(target=cat["coord"][0], observer=obs, time=OBSTIMES_5[:-1], **style_ini)
    # aplt.plot_sky(target=cat["coord"][0], observer=obs, time=OBSTIMES_5[2], **style_mid)
    # aplt.plot_sky(target=cat["coord"][0], observer=obs, time=OBSTIMES_5[-1], **style_end)

    # def find_coo_up(coords, generous=False):
    #     times = OBSTIMES if generous else OBSTIME
    #     horizon = 25*u.deg if generous else 30*u.deg
    #     coo_up = [_coo for _coo in coords
    #               if np.any(observer.target_is_up(times, _coo, horizon=horizon))]
    #     return coo_up

    # == Set plotting style ============================================================== #
    observable_kw = dict(observer=obs, times=OBSTIMES, always=args.always_visible)
    upmask = check_observable(args.min_alt, targets=coo, **observable_kw)
    coo_up = coo[upmask]
    cat_up = cat[upmask]

    fullmask = np.ones(len(cat_up))
    for typ, kwdict in PLOTKW.items():
        typmask = cat_up["Type"].str.startswith(typ)
        add2kw(kwdict, cat_up, coo_up, typmask, plt.cm.viridis)
        fullmask -= typmask
    add2kw(PLOTKW_OTHERS, cat_up, coo_up, fullmask.astype(bool), plt.cm.viridis)
    PLOTKW["others"] = PLOTKW_OTHERS

    cat_up["lowres"] = cat_up["ID"].apply(
        lambda x: f'<img src="{FIGDIR}/{parseID(x)}_{int(x[1:]):03d}.jpg">'
    )
    cat_up["DSS"] = cat_up["ID"].apply(
        lambda x: f'<img src="{FIGDIR}/DSS-200px-{x}.jpg" width=230px>'
    )
    cat_up["DSS-zscale"] = cat_up["ID"].apply(
        lambda x: f'<img src="{FIGDIR}/DSS-200px-{x}-zscale.jpg" width=230px>'
    )
    if args.verbose:
        print(f"{len(cat_up)} objects are visible by the user's criteria.")

    # == Plot ============================================================================ #
    fig, axs = plt.subplots(1, 1, figsize=(9, 9))
    alts_beg = []
    alts_mid = []
    alts_end = []

    for typ, kw in PLOTKW.items():
        for _coo, _color in zip(kw["coo"], kw["colors"]):
            aplt.plot_altitude(
                ax=axs,
                targets=_coo,
                observer=obs,
                time=OBSTIMES,
                min_altitude=args.min_alt,
                style_kwargs=dict(
                    linestyle=kw["ls"],
                    color=_color,
                    alpha=kw["alpha"],
                    linewidth=kw["lw"]
                )
            )
            alts = obs.altaz(OBSTIME_RANGE, target=_coo).alt
            altitudes_beg.append(alts[0].value)
            altitudes_mid.append(alts[1].value)
            altitudes_end.append(alts[2].value)

        if args.verbose:
            print(f"{typ:>6s}: {len(kw['coo']):02d} objects")

    _radec = cat_up["RA"].astype(str) + "<br>" + cat_up["DEC"].astype(str)
    cat_up.sort_values(by=["Type", "DEC"], ascending=False, ignore_index=True, inplace=True)
    cat_up.insert(loc=3, column="RADEC[˚]", value=_radec)
    cat_up["ID"] = cat_up["ID"].apply(mk_wikilink)  # Add wiki links.
    cat_up["ID"] = "<b>" + cat_up["ID"] + "</b><br><br>" + cat_up["Other ID"]

    colnames = [
        f"- {dt.value:.0f} hr<br>altitude",
        (f"{str(args.YYYY)[-2:]}-{args.MM:02d}-{args.DD:02d}<br>"
         + f"{args.HH:02d}:{args.mm:02d}<br>altitude"),
        f"+ {dt.value:.0f} hr<br>altitude"
    ]
    for i, (alts, col) in enumerate(zip([alts_beg, alts_mid, alts_end], colnames)):
        cat_up.insert(loc=i+3, column=col, value=alts)
        cat_up[col] = cat_up[col].apply(alt_color)

    cat_up.drop(columns=COLS2DROP, inplace=True)

    # == Convert to HTML ================================================================= #
    html_str = cat_up.to_html(None, index=False, escape=False)
    html_str = "<pre>" + html_str + "</pre>"
    with open(OUTPUT, "w+") as output:
        output.write(html_str)

    if args.verbose:
        print(f"* Catalog saved to {OUTPUT}")
    # ------------------------------------------------------------------------------------ #

    # for i, (_coo, ls) in enumerate(zip(coo_up, lss)):
    #     aplt.plot_altitude(
    #         targets=_coo, observer=obs, time=OBSTIMES, ax=axs, min_altitude=args.min_alt,
    #         style_kwargs=dict(linestyle=ls, color=colors[i], alpha=0.7, linewidth=2)
    #     )

    moon_phase = obs.moon_phase(OBSTIME).to(u.deg).value
    # in radian, phase=pi is “new”, phase=0 is “full”.
    alt_moon = obs.moon_altaz(OBSTIMES).alt
    axs.plot_date(OBSTIMES.plot_date, alt_moon, '-', color='k', linewidth=6, alpha=0.4,
                  label=f'Moon (θ_full={moon_phase:.0f}˚)')

    upmask_pl = check_observable(args.min_alt_pl, targets=coo_pl, **observable_kw)
    coo_pl_up = coo_pl[upmask_pl]
    if args.verbose:
        print(f"{len(coo_pl_up)} planets are visible under the user's criteria.")
        print(INFOSTR)

    if len(coo_pl_up) > 0:
        for _coo in coo_pl_up:
            aplt.plot_altitude(targets=_coo, observer=obs, time=OBSTIMES, ax=axs, min_altitude=args.min_alt,
                               style_kwargs=dict(color=PLANETS[_coo.name], linewidth=6, alpha=0.3))

    fake_coo = coo_pl[0].copy()
    fake_coo.name = None
    aplt.plot_altitude(targets=fake_coo, observer=obs, time=OBSTIMES, ax=axs,
                       min_altitude=args.min_alt, airmass_yaxis=True, brightness_shading=True,
                       style_kwargs=dict(linestyle=''))

    axs.axhline(30, color='k', linestyle='-')
    axs.legend(ncol=4, bbox_to_anchor=(0.5, -0.15), loc=9,
               prop={"family": "monospace", "size": 10},
               title="<Catalog ID> (<Type>). Use `-v` for detailed explanation for Type.")
    plt.tight_layout()
    plt.show()


# %%
# import requests
# import re
# from pathlib import Path
# from bs4 import BeautifulSoup
# import urllib.request


# SAVEDIR = Path("figs/")
# SAVEDIR.mkdir(exist_ok=True)

# for m_or_c in ["Messier", "Caldwell"]:
#     for i in range(110):
#         name_ID = f"{m_or_c}_{i + 1}"
#         savepath = SAVEDIR/f"{name_ID}.jpg"
#         print(name_ID)
#         if savepath.exists():
#             continue
#         if name_ID == "Messier_102":
#             # Specifically, M102 is NGC 5866  (see https://en.wikipedia.org/wiki/Messier_102)
#         url = "https://en.wikipedia.org/wiki/NGC_5866"
#         else:
#             url = f"https://en.wikipedia.org/wiki/{name_ID}"
#         r = requests.get(url)
#         soup = BeautifulSoup(r.text, 'html.parser')
#         try:
#             infoimgstr = soup.find_all(class_='infobox-image')[0].find_all('img')
#         except IndexError:  # no class "infobox-image"
#             infoimgstr = str(soup.find_all(class_='infobox')[0].find_all("img"))
#         small_img_url = "https:" + re.split(r"src=", str(infoimgstr))[1][1:].split('"')[0]

#         print(small_img_url)
#         urllib.request.urlretrieve(small_img_url, savepath)
#         # re.compile(r"src=").search(str(infoimg)).span
#         # with open(f"figs/{name_ID}.jpg", "wb") as f:
#         #     f.write(requests.get(small_img_url).content)

# %%
