import argparse
import math
from typing import Optional, List

from code_generator_base import CodeGeneratorBase


class Axis(object):
    def __init__(self):
        # current position
        self.pos_current_mm: float = 0
        self.segment_current_nr: int = 0

        # context
        self.direction_increment: bool = True

        # position boundaries
        self.pos_min_mm: float = 0
        self.pos_max_mm: float = 0
        self.pos_travel_mm: float = 0

        # segment boundaries
        self.segment_count: int = 0
        self.segment_length_mm: int = 0
        self.segment_min_nr: int = 0
        self.segment_max_nr: int = 0

        # movement boundaries
        self.movement_segment_start_nr: int = 0
        self.movement_segment_end_nr: int = 0

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
        return self.segment_current_nr >= self.segment_max_nr

    @property
    def is_min_pos_segment(self) -> bool:
        return self.segment_current_nr <= self.segment_min_nr

    @property
    def is_min_or_max_pos_segment(self) -> bool:
        return self.is_min_pos_segment or self.is_max_pos_segment

    def update(self) -> None:
        assert (self.segment_count > 0)
        self.pos_travel_mm = self.pos_max_mm - self.pos_min_mm
        assert (self.pos_travel_mm > 0)
        self.segment_length_mm = self.pos_travel_mm / self.segment_count

        self.segment_min_nr = 0
        self.segment_max_nr = self.segment_count - 1
        assert (self.movement_segment_start_nr >= self.segment_min_nr)
        assert (self.movement_segment_end_nr <= self.segment_max_nr)
        assert (self.movement_segment_start_nr <= self.movement_segment_end_nr)

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
        self.segment_current_nr += direction
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
                self.segment_current_nr = 0
                self.pos_current_mm = 0
                return
        else:
            if self.is_max_pos_segment:
                direction = -1
            elif self.is_min_pos_segment:
                direction = 1

        self.segment_current_nr += direction
        self.pos_current_mm += direction * self.segment_length_mm

    def represents_circle(self):
        return self.segment_count == (self.movement_segment_end_nr - self.movement_segment_start_nr + 1)


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
        self.feed_rate_mm_m = 0

    def update(self):
        self.axes.update()
        self.servo.update()


class CodeGenerator(CodeGeneratorBase):

    def __init__(self, arg_parser: argparse.ArgumentParser):
        super().__init__(arg_parser)

        self.machine: MachineParameter = MachineParameter()

        def uint(x, lower_bound=None, upper_bound=None) -> int:
            i = int(x)
            if i < 0:
                raise ValueError
            if lower_bound and i < lower_bound:
                raise ValueError
            if upper_bound and i > upper_bound:
                raise ValueError
            return i

        g = arg_parser.add_argument_group("Machine settings")
        g.add_argument("--feed_rate_mm_m",
                       help="feed rate in [mm/minute]",
                       default=10000, type=uint)

        g = arg_parser.add_argument_group("Circular settings")
        g.add_argument("--circle_radius",
                       help="circle radius in [mm]",
                       default=1000, type=uint)
        g.add_argument("--circle_segments",
                       help="segments per circle perimeter",
                       default=10, type=uint)
        g.add_argument("--circle_segments_to_move",
                       help="segments to move, range [0,circle_segments-1]",
                       default=9, type=uint)

        g = arg_parser.add_argument_group("Elevation settings")
        g.add_argument("--elevation_min",
                       help="min position along z-axis in [mm]; approximate value; does not correlate with any angle to XY plane or height above Z=0",
                       default=0, type=int)
        g.add_argument("--elevation_max",
                       help="max position along z-axis in [mm]; approximate value; does not correlate with any angle to XY plane or height above Z=0",
                       default=400, type=int)
        g.add_argument("--elevation_segments",
                       help="segments per total elevation travel",
                       default=10, type=uint)
        g.add_argument("--elevation_segment_start",
                       help="steps to move from, range [1,elevation_step_end]",
                       default=0, type=uint)
        g.add_argument("--elevation_segment_end",
                       help="steps to move to, range [1,elevation_steps], value > elevation_step_start",
                       default=9, type=uint)

        g = arg_parser.add_argument_group("Servo settings")
        g.add_argument("--servo_position_release",
                       help="servo position when not actuating, range [0-10000]; 0=servo_off, 1=servo_min, 10000=servo_max",
                       default=1, type=uint)
        g.add_argument("--servo_position_actuate",
                       help="servo position when actuating, range [0-10000]; 0=servo_off, 1=servo_min, 10000=servo_max",
                       default=1000, type=uint)
        g.add_argument("--servo_pre_actuate_dwell",
                       help=" delay in [s] to wait before actuating, range [0.0,n]",
                       default=0.8, type=float)
        g.add_argument("--servo_actuate_dwell",
                       help=" delay in [s] to wait while actuated, range [0.0,n]",
                       default=0.2, type=float)
        g.add_argument("--servo_post_actuate_dwell",
                       help=" delay in [s] to wait after released, range [0.0,n]",
                       default=0.2, type=float)

    def setup(self, args: Optional[argparse.Namespace]):
        # machine args
        self.machine.feed_rate_mm_m = args.feed_rate_mm_m

        # x-axis
        self.machine.axes.circular.radius_mm = args.circle_radius
        self.machine.axes.circular.segment_count = args.circle_segments
        self.machine.axes.circular.movement_segment_start_nr = 0
        self.machine.axes.circular.movement_segment_end_nr = args.circle_segments_to_move

        # z-axis
        self.machine.axes.elevation.pos_min_mm = args.elevation_min
        self.machine.axes.elevation.pos_max_mm = args.elevation_max
        self.machine.axes.elevation.segment_current_nr = args.elevation_segment_start
        self.machine.axes.elevation.segment_count = args.elevation_segments
        self.machine.axes.elevation.movement_segment_start_nr = args.elevation_segment_start
        self.machine.axes.elevation.movement_segment_end_nr = args.elevation_segment_end

        # shutter servo
        self.machine.servo.pos_release = args.servo_position_release
        self.machine.servo.pos_actuate = args.servo_position_actuate
        self.machine.servo.pre_actuate_delay_s = args.servo_pre_actuate_dwell
        self.machine.servo.actuate_delay_s = args.servo_actuate_dwell
        self.machine.servo.post_actuate_delay_s = args.servo_post_actuate_dwell

        self.machine.update()

        info = f"""
Generator: {self.name}
  {self.description}

Machine settings
  feed rate [mm/min]:   {self.machine.feed_rate_mm_m} 
Circular info
  x-axis [mm]
    min (soft limit):   {self.machine.axes.circular.pos_min_mm}
    max (soft limit):   {self.machine.axes.circular.pos_max_mm}
    travel (perimeter): {self.machine.axes.circular.perimeter_mm}
    radius:             {self.machine.axes.circular.radius_mm}
  segment(s):           {self.machine.axes.circular.segment_count}
    length [mm]:        {self.machine.axes.circular.segment_length_mm}
    move from #:        {self.machine.axes.circular.movement_segment_start_nr}
    move to   #:        {self.machine.axes.circular.movement_segment_end_nr}
    represent circle:   {"true" if self.machine.axes.circular.represents_circle() else "false"}
Elevation info
  z-axis [mm]
    min:                {self.machine.axes.elevation.pos_min_mm}
    max:                {self.machine.axes.elevation.pos_max_mm}
    travel:             {self.machine.axes.elevation.pos_travel_mm}
  segment(s):           {self.machine.axes.elevation.segment_count}
    length [mm]:        {self.machine.axes.elevation.segment_length_mm}
    move from #:        {self.machine.axes.elevation.movement_segment_start_nr}
    move to   #:        {self.machine.axes.elevation.movement_segment_end_nr}
Servo info
  position
    release:            {self.machine.servo.pos_release}
    actuate:            {self.machine.servo.pos_actuate}
  actuate delay [s]
    pre actuate:        {"{:.1f}".format(self.machine.servo.pre_actuate_delay_s)}
    while actuating:    {"{:.1f}".format(self.machine.servo.actuate_delay_s)}
    post actuate:       {"{:.1f}".format(self.machine.servo.post_actuate_delay_s)}
"""
        print(info)

    @property
    def name(self) -> str:
        return "circular-first-then-elevation"

    @property
    def description(self) -> str:
        return "Moves through circular segments (min to max and vice vesa) and advances one elevation step (min to max) at each circular boundary. Repeats until elevation max is reached."

    def get_preamble(self) -> List[str]:
        return f"""
; home
$H
; absolute positioning
G90
; stop spindle/servo
M5
; disable servo signal
S0

; feed rate
F{self.machine.feed_rate_mm_m}
; unit is mm
G21
; work in machine coordinates
G53

; set current position manually to (X,Z)=(0,0)
G92 X0 Z0
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
""" \
            .splitlines()

    def _generate_servo_code_for_current_position(self) -> List[str]:
        return f"""
G4 P{"{:.1f}".format(self.machine.servo.pre_actuate_delay_s)}
S{self.machine.servo.pos_actuate}
G4 P{"{:.1f}".format(self.machine.servo.actuate_delay_s)}
S{self.machine.servo.pos_release}
G4 P{"{:.1f}".format(self.machine.servo.post_actuate_delay_s)}
""" \
            .splitlines()

    def _generate_code_for_current_position(self, reset_circular_position=False, include_elevation=False) -> List[str]:
        code = list()
        code.append(f"X{'{:.1f}'.format(self.machine.axes.circular.pos_current_mm)}")
        if reset_circular_position:
            code.append("; set current position manually to X=0")
            code.append(f"G92 X0")
        if include_elevation:
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
        return f"""
; re-enable stepper driver idling of 25ms and request movement of 0mm to activate new parameter
$1=25
G91
Z+0.01
Z-0.01

; stop servo signal, stop spindle, end program
S0
M5
M2

; program terminated
""" \
            .splitlines()
