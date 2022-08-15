# gcode-generator
Parametrizable python script for creating g-code files for the photogrammetry scanner.
The g-code file is then uploaded manually to the scanner and processed. 
The code describes the scanner movement and cammera shutter actions.

**Example:**
```
$ ./main.py --force --compress   

Generator: circular-first-then-elevation
  Moves through circular segments (min to max and vice vesa) and advances one elevation step (min to max) at each circular boundary. Repeats until elevation max is reached.

Machine settings
  feed rate [mm/min]:   10000 
Circular info
  x-axis [mm]
    min (soft limit):   0
    max (soft limit):   6283.185307179586
    travel (perimeter): 6283.185307179586
    radius:             1000
  segment(s):           10
    length [mm]:        628.3185307179585
    move from #:        0
    move to   #:        9
    represent circle:   true
Elevation info
  z-axis [mm]
    min:                0
    max:                400
    travel:             400
  segment(s):           10
    length [mm]:        40.0
    move from #:        0
    move to   #:        9
Servo info
  position
    release:            1
    actuate:            1000
  actuate delay [s]
    pre actuate:        0.8
    while actuating:    0.2
    post actuate:       0.2

exported 4285 bytes g-code to file './out.g' using generator 'circular-first-then-elevation' (Moves through circular segments (min to max and vice vesa) and advances one elevation step (min to max) at each circular boundary. Repeats until elevation max is reached.)

$ cat out.g
$H
G90
M5
S0
F10000
G21
G53
G92 X0 Z0
...
S0
M5
M2

```

**Usage:**

```
$ ./main.py --help
usage: main.py [-h] [-o OUTPUT] [-f] [-c] [--feed_rate_mm_m FEED_RATE_MM_M] [--circle_radius CIRCLE_RADIUS] [--circle_segments CIRCLE_SEGMENTS] [--circle_segments_to_move CIRCLE_SEGMENTS_TO_MOVE]
               [--elevation_min ELEVATION_MIN] [--elevation_max ELEVATION_MAX] [--elevation_segments ELEVATION_SEGMENTS] [--elevation_segment_start ELEVATION_SEGMENT_START]
               [--elevation_segment_end ELEVATION_SEGMENT_END] [--servo_position_release SERVO_POSITION_RELEASE] [--servo_position_actuate SERVO_POSITION_ACTUATE]
               [--servo_pre_actuate_dwell SERVO_PRE_ACTUATE_DWELL] [--servo_actuate_dwell SERVO_ACTUATE_DWELL] [--servo_post_actuate_dwell SERVO_POST_ACTUATE_DWELL]

optional arguments:
  -h, --help            show this help message and exit

Output:
  -o OUTPUT, --output OUTPUT
                        output file name (default: ./out.g)
  -f, --force           overwrite existing file (default: False)
  -c, --compress        remove comments, empty lines and strip whitespaces (default: False)

Machine settings:
  --feed_rate_mm_m FEED_RATE_MM_M
                        feed rate in [mm/minute] (default: 10000)

Circular settings:
  --circle_radius CIRCLE_RADIUS
                        circle radius in [mm] (default: 1000)
  --circle_segments CIRCLE_SEGMENTS
                        segments per circle perimeter (default: 10)
  --circle_segments_to_move CIRCLE_SEGMENTS_TO_MOVE
                        segments to move, range [0,circle_segments-1] (default: 9)

Elevation settings:
  --elevation_min ELEVATION_MIN
                        min position along z-axis in [mm]; approximate value; does not correlate with any angle to XY plane or height above Z=0 (default: 0)
  --elevation_max ELEVATION_MAX
                        max position along z-axis in [mm]; approximate value; does not correlate with any angle to XY plane or height above Z=0 (default: 400)
  --elevation_segments ELEVATION_SEGMENTS
                        segments per total elevation travel (default: 10)
  --elevation_segment_start ELEVATION_SEGMENT_START
                        steps to move from, range [1,elevation_step_end] (default: 0)
  --elevation_segment_end ELEVATION_SEGMENT_END
                        steps to move to, range [1,elevation_steps], value > elevation_step_start (default: 9)

Servo settings:
  --servo_position_release SERVO_POSITION_RELEASE
                        servo position when not actuating, range [0-10000]; 0=servo_off, 1=servo_min, 10000=servo_max (default: 1)
  --servo_position_actuate SERVO_POSITION_ACTUATE
                        servo position when actuating, range [0-10000]; 0=servo_off, 1=servo_min, 10000=servo_max (default: 1000)
  --servo_pre_actuate_dwell SERVO_PRE_ACTUATE_DWELL
                        delay in [s] to wait before actuating, range [0.0,n] (default: 0.8)
  --servo_actuate_dwell SERVO_ACTUATE_DWELL
                        delay in [s] to wait while actuated, range [0.0,n] (default: 0.2)
  --servo_post_actuate_dwell SERVO_POST_ACTUATE_DWELL
                        delay in [s] to wait after released, range [0.0,n] (default: 0.2)

```
