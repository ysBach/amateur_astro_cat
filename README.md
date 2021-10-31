# find_amateur_astro_target
Yoonsoo P. Bach (@ysBach)

This work is derived from the "서울대학교 천문대 공개행사", a subproject of "서울대학교 연구성과사회환원 프로그램" at Seoul National University, S. Korea.



Find which **amateur astronomy targets** that are above the horizon at given time, and showing the altitude/airmass plot.

Catalogs supported at this moment are [Messier](https://en.wikipedia.org/wiki/Messier_object) and [Caldwell](https://en.wikipedia.org/wiki/Caldwell_catalogue).



Default location at Seoul, South Korea.



## Dependency

* python 3.6+
* pytz
* numpy
* pandas
* astropy
* **astroplan**
* matplotlib
* rich (optional)



### Install 

First, install Anaconda python distribution. Then all may have been installed, except for `astroplan`. Install it by:

```
$ conda install -c astropy astroplan
```



(OPTIONAL: Package `rich` is used for nothing but nicer output on terminal. You may install by `pip install rich`, but it is **not necessary**.)



To use this simple python script,

```
$ cd <where you want to save it>
$ git clone https://github.com/ysBach/find_amateur_astro_target.git
$ cd find_amateur_astro_target
$ python find_targets.py -C  # slightly better
```

When you run the script for the **first time**, it will take some time, like **~ 5 minutes** (as it tries to query the RA/DEC information of the objects from online).

You may play with it - see the Usage below.



## Usage

### 1. The simplest example

```
$ python find_targets.py
```

It will use all ~200 targets, using the current time ± 2 hour at Seoul. Any object above minimum altitude 30˚ will be plotted.



### 2. Practical usage for 공진단

#### 2-1. First run

First, check for ALL the objects above the horizon on the day. I will test with 

* 2021-11-12 20:30:00 [KST] (given by ``2021 11 12 20 30``) 
* duration of ± 1 hour (given by `-d 1`)
* I want to see only those are above 30˚ ALL the time (use `-A`)
* I want to remove those without common nickname (use `-N`)
* save all target list as ``test.html`` (`-o test.html`)
* use verbose option (`-v`)

```
$ python find_targets.py 2021 11 12 20 30 00 -o first.html -d 1 -vAN
```

Output:

```
Abbreviations for "Type" column
[...]

Date & Time : 2021-11-12 20:30:00+09:00 (Asia/Seoul)
 lon , lat  : 127.00˚, 37.50˚
96 objects are selected by the user.
26 objects are visible by the user's criteria.
Catalog saved to first.html
3 planets are visible under the user's criteria.
```

The plot is messy, but it is intended (because there are 26 objects!).

![](examples/Figure_1.png)

* **NOTE**: line style is grouped based on the type of the objects (cluster, neubla, galaxy, otehrs)
* **NOTE**: For the Moon, ``θ_full`` means the 180˚ - (Sun-Earth-Moon angle), i.e., the angle for the Moon to travel to become a full moon.

The output HTML will look something like this:

![](examples/Figure_2.png)

It shows the ID (C: Caldwell, M: Messier), NGC/IC IDs, common names, etc. On top of these, it gives you **link to Wikipedia**, and the **35'x35' view by DSS** in linear scale and zscale. The red boxes are 21'x21', which is the FoV of SNU-SAO 1m telescope with STX-16803.

#### 2. Second run

Now, considering the time limit and the interest of the audience (e.g., depending on the topic of the lecture given before the observation), **let's select few target candidates**. 

On 2021-11-12, we have a lecture on Sombrero galaxy (M104), but it is not visible, unfortunately. Similar galaxies, S/E types, can be chosen from the list above. I will select M31 (Andromeda), M33 (Pinwheel galaxy), C12 (Fireworks galaxy), C23 (Silver silver galaxy). Also, let me choose an open cluster that may be attractive to general audience, C13 (Owl cluster). Unfortunately, we have no globular cluster! If you want, you can go back to the first step and run withou `-C`. I will skip that. I will also add two nebulae, the Cave Nebula, C9, and Little Dumbbell nebula, M76.

* Select targets by `-t M31 M33 C12 C23 C13 C9 M76`

```
$ python find_targets.py 2021 11 12 20 30 00 -o second.html -d 1 -v -t M31 M33 C12 C23 C13 C9 M76
```

The plot looks simpler, but you have to note that M72 and M45 can be below altitude 30˚ (the lower limit for SNU-SAO 1m telescope) during the ± 1hour duration.

![](examples/Figure_3.png)

So in this open astro observation, you may select few of these, depending on the time you have :)
