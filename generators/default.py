import argparse
import math
from typing import Optional, List

from code_generator_base import CodeGeneratorBase
from helpers import assert_uint, environ_or_default


class Axis(object):
    def __init__(self):
        # current position
        self.pos_current_mm: float = 0
        self.segment_current_idx: int = 0

        # context
        self.direction_increment: bool = True

        # position boundaries
        self.pos_min_mm: float = 0
        self.pos_max_mm: float = 0
        self.pos_travel_mm: float = 0

        # segment boundaries
        self.segment_count: int = 0
        self.segment_length_mm: int = 0
        self.segment_min_idx: int = 0
        self.segment_max_idx: int = 0

        # movement boundaries
        self.movement_segment_start_idx: int = 0
        self.movement_segment_stop_idx: int = 0

    @property
    def _is_max_pos_mm(self) -> bool:
        return self.pos_current_mm >= self.pos_max_mm

    @property
    def _is_min_pos_mm(self) -> bool:
        return self.pos_current_mm <= self.pos_max_mm

    @property
    def _is_min_or_max_pos_mm(self) -> bool:
        return self._is_min_pos_mm or self._is_max_pos_mm

    @property
    def is_max_pos_segment(self) -> bool:
        return self.segment_current_idx >= self.segment_max_idx

    @property
    def is_min_pos_segment(self) -> bool:
        return self.segment_current_idx <= self.segment_min_idx

    @property
    def is_min_or_max_pos_segment(self) -> bool:
        return self.is_min_pos_segment or self.is_max_pos_segment

    def update(self) -> None:
        assert (self.segment_count > 0)
        self.pos_travel_mm = self.pos_max_mm - self.pos_min_mm
        assert (self.pos_travel_mm > 0)
        self.segment_length_mm = self.pos_travel_mm / self.segment_count

        self.segment_min_idx = 0
        self.segment_max_idx = self.segment_count - 1
        assert (self.movement_segment_start_idx >= self.segment_min_idx)
        assert (self.movement_segment_stop_idx <= self.segment_max_idx)
        assert (self.movement_segment_start_idx <= self.movement_segment_stop_idx)

    def compute_next_position(self) -> None:
        raise NotImplementedError()


class LinearAxis(Axis):

    def update(self) -> None:
        super(LinearAxis, self).update()

    def compute_next_position(self):
        """
        Movement oscillates from min to max and vice versa.
        """
        if self.is_min_pos_segment:
            self.direction_increment = True
        elif self.is_max_pos_segment:
            self.direction_increment = False

        direction = 1 if self.direction_increment else -1
        self.segment_current_idx += direction
        self.pos_current_mm += direction * self.segment_length_mm


class CircularAxis(Axis):

    def __init__(self):
        super().__init__()
        self.radius_mm: int = 0
        self.perimeter_mm: float = 0

    def update(self) -> None:
        assert (self.radius_mm > 0)
        self.perimeter_mm = (math.pi + math.pi) * self.radius_mm
        self.pos_min_mm = 0
        self.pos_max_mm = self.perimeter_mm
        super(CircularAxis, self).update()

    def compute_next_position(self):
        """
        If num_segments_to_move = segments_count -> move forward only
        If num_segments_to_move < segments_count -> oscillate from min to max and vice versa
        if num_segments_to_move > segments_count -> assert(False)
        """

        direction = 1
        if self.represents_circle():
            if self.is_max_pos_segment:
                self.segment_current_idx = 0
                self.pos_current_mm = 0
                return
        else:
            if self.is_max_pos_segment:
                direction = -1
            elif self.is_min_pos_segment:
                direction = 1

        self.segment_current_idx += direction
        self.pos_current_mm += direction * self.segment_length_mm

    def represents_circle(self):
        return self.segment_count == (self.movement_segment_stop_idx - self.movement_segment_start_idx + 1)


class Axes(object):
    def __init__(self):
        self.circular = CircularAxis()
        self.elevation = LinearAxis()

    def update(self):
        self.circular.update()
        self.elevation.update()


class Servo(object):
    def __init__(self):
        self.pos_release: int = 0
        self.pos_actuate: int = 0
        self.pre_actuate_delay_s: float = 0
        self.actuate_delay_s: float = 0
        self.post_actuate_delay_s: float = 0

    def update(self):
        pass


class MachineParameter(object):
    def __init__(self):
        self.axes: Axes = Axes()
        self.servo: Servo = Servo()
        self.feed_rate_mm_m = 0  # for combined moves which may involve multipla axes
        self.feed_rate_x_mm_m = 0
        self.feed_rate_z_mm_m = 0
        self.acceleration_x_mm_s2 = 0
        self.acceleration_z_mm_s2 = 0
        self.steps_per_mm_x = 0
        self.steps_per_mm_z = 0
        self.homing_seek_rate = 0
        self.homing_rate = 0

    def update(self):
        self.axes.update()
        self.servo.update()


class CodeGenerator(CodeGeneratorBase):

    def __init__(self, arg_parser: argparse.ArgumentParser):
        super().__init__(arg_parser)
        self.machine: MachineParameter = MachineParameter()
        uint = lambda x: assert_uint(x)

        g = arg_parser.add_argument_group("Machine settings")
        g.add_argument("--feed_rate",
                       help="max feed rate [mm/minute] for travel (may involve multiple axes); if 0 falls back to machine defaults; env: FEED_RATE",
                       default=environ_or_default("FEED_RATE", 20000), type=uint)
        g.add_argument("--feed_rate_circular",
                       help="feed rate [mm/minute] in circular direction (X-axis); if 0 falls back to machine defaults; env: FEED_RATE_CIRCULAR",
                       default=environ_or_default("FEED_RATE_CIRCULAR", 20000), type=uint)
        g.add_argument("--feed_rate_elevation",
                       help="max feed rate [mm/minute] in elevation direction (Z-axis); if 0 falls back to machine defaults; env: FEED_RATE_ELEVATION",
                       default=environ_or_default("FEED_RATE_ELEVATION", 800), type=uint)
        g.add_argument("--acceleration_circular",
                       help="max feed rate [mm/s²] in circular direction (X-axis); if 0 falls back to machine defaults; env: ACCELERATION_CIRCULAR",
                       default=environ_or_default("ACCELERATION_CIRCULAR", 300), type=uint)
        g.add_argument("--acceleration_elevation",
                       help="max feed rate [mm/s²] in elevation direction (Z-axis); if 0 falls back to machine defaults; env: ACCELERATION_ELEVATION",
                       default=environ_or_default("ACCELERATION_ELEVATION", 7), type=uint)
        g.add_argument("--steps_per_mm_circular",
                       help="steps per [steps/mm] in circular direction (X-axis); (steps_revolution*micro_steps)/(2*r*Pi); if 0 falls back to machine defaults; env: STEPS_PER_MM_CIRCULAR",
                       default=environ_or_default("STEPS_PER_MM_CIRCULAR", (200.0 * 16) / (2.0 * 36.5 * 3.14159)), type=uint)
        g.add_argument("--steps_per_mm_elevation",
                       help="steps per [steps/mm] in circular direction (X-axis); steps_revolution*micro_steps)/pitch; if 0 falls back to machine defaults; env: STEPS_PER_MM_ELEVATION",
                       default=environ_or_default("STEPS_PER_MM_CIRCULAR", (200.0 * 16.0) / 1.25), type=uint)
        g.add_argument("--homing_seek_rate",
                       help="speed [mm/minute] for seeking home; seeking is the fast process, homing (slow process) will be homing_seek_rate/2; "
                            "if 0 falls back to machine defaults; env: HOMING_SEEK_RATE",
                       default=environ_or_default("HOMING_SEEK_RATE", 600), type=uint)

        g = arg_parser.add_argument_group("Circular settings")
        g.add_argument("--circle_radius",
                       help="circle radius in [mm]; env: CIRCLE_RADIUS",
                       default=environ_or_default("CIRCLE_RADIUS", 489), type=uint)
        g.add_argument("--circle_segments",
                       help="segments per circle perimeter, range [1,n]; env: CIRCLE_SEGMENTS",
                       default=environ_or_default("CIRCLE_SEGMENTS", 4), type=uint)
        g.add_argument("--circle_segment_start",
                       help="segment to start at, range [1,circle_segments-1]; env: CIRCLE_SEGMENT_START",
                       default=environ_or_default("CIRCLE_SEGMENT_START", 0), type=uint)
        g.add_argument("--circle_segment_stop",
                       help="last segment to move to, range [0,elevation_segments-1], value >= elevation_segment_start; env: CIRCLE_SEGMENT_STOP",
                       default=environ_or_default("CIRCLE_SEGMENT_STOP", 3), type=uint)

        g = arg_parser.add_argument_group("Elevation settings")
        g.add_argument("--elevation_min",
                       help="min position along z-axis in [mm]; approximate value; does not correlate with any angle to XY plane or height above Z=0; env: ELEVATION_MIN",
                       default=environ_or_default("ELEVATION_MIN", 0), type=int)
        g.add_argument("--elevation_max",
                       help="max position along z-axis in [mm]; approximate value; does not correlate with any angle to XY plane or height above Z=0; env: ELEVATION_MAX",
                       default=environ_or_default("ELEVATION_MAX", 400), type=int)
        g.add_argument("--elevation_segments",
                       help="segments per elevation travel, range [1,n]; env: ELEVATION_SEGMENTS",
                       default=environ_or_default("ELEVATION_SEGMENTS", 3), type=uint)
        g.add_argument("--elevation_segment_start",
                       help="segment to start at, range [1,elevation_segments-1]; env: ELEVATION_SEGMENT_START",
                       default=environ_or_default("ELEVATION_SEGMENT_START", 0), type=uint)
        g.add_argument("--elevation_segment_stop",
                       help="last segment to move to, range [0,elevation_segments-1], value >= elevation_segment_start; env: ELEVATION_SEGMENT_STOP",
                       default=environ_or_default("ELEVATION_SEGMENT_STOP", 2), type=uint)

        g = arg_parser.add_argument_group("Servo settings")
        g.add_argument("--servo_position_release",
                       help="servo position when not actuating, range [0-1000]; 0=servo_off, 1=servo_min, 1000=servo_max; env: SERVO_POSITION_RELEASE",
                       default=environ_or_default("SERVO_POSITION_RELEASE", 1), type=uint)
        g.add_argument("--servo_position_actuate",
                       help="servo position when actuating, range [0-1000]; 0=servo_off, 1=servo_min, 1000=servo_max; env: SERVO_POSITION_ACTUATE",
                       default=environ_or_default("SERVO_POSITION_ACTUATE", 1000), type=uint)
        g.add_argument("--servo_pre_actuate_dwell",
                       help=" delay in [s] to wait before actuating, range [0.0,n]; env: SERVO_PRE_ACTUATE_DWELL",
                       default=environ_or_default("SERVO_PRE_ACTUATE_DWELL", 0.8), type=float)
        g.add_argument("--servo_actuate_dwell",
                       help=" delay in [s] to wait while actuated, range [0.0,n]; env: SERVO_ACTUATE_DWELL",
                       default=environ_or_default("SERVO_ACTUATE_DWELL", 0.2), type=float)
        g.add_argument("--servo_post_actuate_dwell",
                       help=" delay in [s] to wait after released, range [0.0,n]; env: SERVO_POST_ACTUATE_DWELL",
                       default=environ_or_default("SERVO_POST_ACTUATE_DWELL", 0.2), type=float)

    def setup(self, args: Optional[argparse.Namespace]):
        # machine args
        self.machine.feed_rate_mm_m = args.feed_rate
        self.machine.feed_rate_x_mm_m = args.feed_rate_circular
        self.machine.feed_rate_z_mm_m = args.feed_rate_elevation
        self.machine.acceleration_x_mm_s2 = args.acceleration_circular
        self.machine.acceleration_z_mm_s2 = args.acceleration_elevation
        self.machine.steps_per_mm_x = args.steps_per_mm_circular
        self.machine.steps_per_mm_z = args.steps_per_mm_elevation
        self.machine.homing_seek_rate = args.homing_seek_rate
        self.machine.homing_rate = int(self.machine.homing_seek_rate / 2)

        # x-axis
        self.machine.axes.circular.radius_mm = args.circle_radius
        self.machine.axes.circular.segment_count = args.circle_segments
        self.machine.axes.circular.segment_current_idx = args.circle_segment_start
        self.machine.axes.circular.movement_segment_start_idx = args.circle_segment_start
        self.machine.axes.circular.movement_segment_stop_idx = args.circle_segment_stop

        # z-axis
        self.machine.axes.elevation.pos_min_mm = args.elevation_min
        self.machine.axes.elevation.pos_max_mm = args.elevation_max
        self.machine.axes.elevation.segment_count = args.elevation_segments
        self.machine.axes.elevation.segment_current_idx = args.elevation_segment_start
        self.machine.axes.elevation.movement_segment_start_idx = args.elevation_segment_start
        self.machine.axes.elevation.movement_segment_stop_idx = args.elevation_segment_stop

        # shutter servo
        self.machine.servo.pos_release = args.servo_position_release
        self.machine.servo.pos_actuate = args.servo_position_actuate
        self.machine.servo.pre_actuate_delay_s = args.servo_pre_actuate_dwell
        self.machine.servo.actuate_delay_s = args.servo_actuate_dwell
        self.machine.servo.post_actuate_delay_s = args.servo_post_actuate_dwell

        self.machine.update()
        print(self.settings)

    @property
    def suggested_file_name(self):
        # Note: microcontroller file system will not support long file names
        return f"{self.name}-f{self.machine.feed_rate_mm_m}-fx{self.machine.feed_rate_x_mm_m}-fz{self.machine.feed_rate_z_mm_m}" \
               f"-ax{self.machine.acceleration_x_mm_s2}-az{self.machine.acceleration_z_mm_s2}" \
               f"-circ_seg_{self.machine.axes.circular.segment_min_idx}_to_{self.machine.axes.circular.segment_max_idx}_from_{self.machine.axes.circular.segment_count}" \
               f"-elev_seg_{self.machine.axes.elevation.segment_min_idx}_to_{self.machine.axes.elevation.segment_max_idx}_from_{self.machine.axes.elevation.segment_count}" \
               f".g"

    @property
    def settings(self):
        return f"""Generator: {self.name}
  {self.description}
Machine settings
  max feed rate [mm/min]
    travel:             {self.machine.feed_rate_mm_m}
    circular:           {self.machine.feed_rate_x_mm_m}
    elevation:          {self.machine.feed_rate_z_mm_m}
  acceleration [mm/s²]
    circular:           {self.machine.acceleration_x_mm_s2}
    elevation:          {self.machine.acceleration_z_mm_s2}
  homing [mm/min]
    seek rate (fast):   {self.machine.homing_seek_rate}
    homing rate (slow): {self.machine.homing_rate}
Circular info
  x-axis [mm]
    min (soft limit):   {self.machine.axes.circular.pos_min_mm}
    max (soft limit):   {self.machine.axes.circular.pos_max_mm}
    travel (perimeter): {self.machine.axes.circular.perimeter_mm}
    radius:             {self.machine.axes.circular.radius_mm}
  segment(s):           {self.machine.axes.circular.segment_count}
    length [mm]:        {self.machine.axes.circular.segment_length_mm}
    move from index:    {self.machine.axes.circular.movement_segment_start_idx}
    move to index:      {self.machine.axes.circular.movement_segment_stop_idx}
    represent circle:   {"true" if self.machine.axes.circular.represents_circle() else "false"}
Elevation info
  z-axis [mm]
    min:                {self.machine.axes.elevation.pos_min_mm}
    max:                {self.machine.axes.elevation.pos_max_mm}
    travel:             {self.machine.axes.elevation.pos_travel_mm}
  segment(s):           {self.machine.axes.elevation.segment_count}
    length [mm]:        {self.machine.axes.elevation.segment_length_mm}
    move from index:    {self.machine.axes.elevation.movement_segment_start_idx}
    move to index:      {self.machine.axes.elevation.movement_segment_stop_idx}
Servo info
  position
    release:            {self.machine.servo.pos_release}
    actuate:            {self.machine.servo.pos_actuate}
  actuate delay [s]
    pre actuate:        {"{:.1f}".format(self.machine.servo.pre_actuate_delay_s)}
    while actuating:    {"{:.1f}".format(self.machine.servo.actuate_delay_s)}
    post actuate:       {"{:.1f}".format(self.machine.servo.post_actuate_delay_s)}
"""

    @property
    def name(self) -> str:
        return "circular-first-then-elevation"

    @property
    def description(self) -> str:
        return "Moves through circular segments (min to max and vice vesa) and advances one elevation step (min to max) at each circular boundary. Repeats until elevation max is reached."

    def get_preamble(self) -> List[str]:
        nl = '\n'
        return f"""; ----- info -----
{nl.join([f"; {l}" for l in self.settings.splitlines()])}
; ----- preamble -----
; steps per mm
{f'$100={round(self.machine.steps_per_mm_x, 2)}' if self.machine.steps_per_mm_x > 0 else ''}
{f'$102={round(self.machine.steps_per_mm_z, 2)}' if self.machine.steps_per_mm_z > 0 else ''}
; acceleration
{f'$120={self.machine.acceleration_x_mm_s2}' if self.machine.acceleration_x_mm_s2 > 0 else ''}
{f'$122={self.machine.acceleration_z_mm_s2}' if self.machine.acceleration_z_mm_s2 > 0 else ''}
; axis feed rates
{f'$110={self.machine.feed_rate_x_mm_m}' if self.machine.feed_rate_x_mm_m > 0 else ''}
{f'$112={self.machine.feed_rate_z_mm_m}' if self.machine.feed_rate_z_mm_m > 0 else ''}
; homing feed rate
{f'$24={self.machine.homing_rate}' if self.machine.homing_rate > 0 else ''}
{f'$25={self.machine.homing_seek_rate}' if self.machine.homing_seek_rate > 0 else ''}
; home
$H
; unit is mm
G21
; work in machine coordinates
G53
; set current position manually to (X,Z)=(0,0)
G92 X0 Y0 Z0
; absolute positioning
G90
; stop spindle/servo
M5
; disable servo signal
S0
; travel feed rate
{f'F{self.machine.feed_rate_mm_m}' if self.machine.feed_rate_mm_m > 0 else ''}
; move to position (0,0): eliminates one GRBL error message
G1 X0 Z0
; enable spindle/servo
M3
; move servo to min pos
S{self.machine.servo.pos_release}
; disable stepper driver idling
$1=255
; go to Z-start position
Z{self.machine.axes.elevation.pos_current_mm}
; ----- program -----
""" \
            .splitlines()

    def _generate_servo_code_for_current_position(self) -> List[str]:
        return f"""G4 P{"{:.1f}".format(self.machine.servo.pre_actuate_delay_s)}
S{self.machine.servo.pos_actuate}
G4 P{"{:.1f}".format(self.machine.servo.actuate_delay_s)}
S{self.machine.servo.pos_release}
G4 P{"{:.1f}".format(self.machine.servo.post_actuate_delay_s)}
""" \
            .splitlines()

    def _generate_code_for_current_position(self, reset_circular_position=False, include_elevation=False) -> List[str]:
        code = list()
        if reset_circular_position:
            code.append("; reset current position manually to X=0")
            code.append(f"G92 X0")
            code.append(f"\n; segment (circular,elevation)=({self.machine.axes.circular.segment_current_idx},{self.machine.axes.elevation.segment_current_idx})")
            code.append(f"X{'{:.1f}'.format(self.machine.axes.circular.pos_current_mm)}")
        else:
            code.append(f"\n; segment (circular,elevation)=({self.machine.axes.circular.segment_current_idx},{self.machine.axes.elevation.segment_current_idx})")
            code.append(f"X{'{:.1f}'.format(self.machine.axes.circular.pos_current_mm)}")
        if include_elevation:
            code.append("; enhance elevation")
            code.append(f"Z{'{:.1f}'.format(self.machine.axes.elevation.pos_current_mm)}")
        code.extend(self._generate_servo_code_for_current_position())
        return code

    def get_program(self) -> List[str]:
        program: List[str] = list()

        flush_elevation = True
        reset_circular_position = False
        while True:
            program.extend(self._generate_code_for_current_position(reset_circular_position, flush_elevation))
            flush_elevation = False
            reset_circular_position = False
            if self.machine.axes.circular.is_max_pos_segment and self.machine.axes.elevation.is_max_pos_segment:
                break
            self.machine.axes.circular.compute_next_position()
            if self.machine.axes.circular.is_min_pos_segment:
                self.machine.axes.elevation.compute_next_position()
                flush_elevation = True
                reset_circular_position = True

        return program

    def get_postamble(self) -> List[str]:
        return f"""; ----- postamble -----
; re-enable stepper driver idling of 25ms and request movement of 0mm to activate new parameter
$1=25
G90
Z0.01
Z0
; stop servo signal, stop spindle, end program
S0
M5
M2
; ----- program end -----

""" \
            .splitlines()
