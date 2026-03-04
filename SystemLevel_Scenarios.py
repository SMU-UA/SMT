import io
import json
import time
import urllib.request
from pathlib import Path
from datetime import datetime

from typhoon.api.schematic_editor import SchematicAPI

import allure
import matplotlib.pyplot as plt
import pytest
import typhoon.test.reporting.messages as report
import typhoon.api.hil as hil
from typhoon.api.schematic_editor import model
from typhoon.test import capture, signals
from typhoon.test.ranges import around
from typhoon.test.capture import start_capture

mdl = SchematicAPI()
# list of harmonics
harmonics = []
harmonics0 = []
# tuples that contains harmonic settings
# (harmonic_number,rms,phase)
harmonic2 = (2, 0.0338, 0)
harmonic3 = (3, 0.2, 126)
harmonic4 = (4, 0.015, 111)
harmonic5 = (5, 0.01, 129)
harmonic6 = (6, 0.006, 0)
harmonic7 = (7, 0.01, 139.4)
harmonic8 = (8, 0.0088, 0)
harmonic9 = (9, 0.02, 172.4)
harmonic10 = (10, 0.007, 172)
harmonic11= (11, 0.004, 170)
# store harmonics
harmonics.append(harmonic2)
harmonics.append(harmonic3)
harmonics.append(harmonic4)
harmonics.append(harmonic5)
harmonics.append(harmonic6)
harmonics.append(harmonic7)
harmonics.append(harmonic8)
harmonics.append(harmonic9)
harmonics.append(harmonic10)
harmonics.append(harmonic11)


harmonic2_0 = (2, 0.0, 0)
harmonic3_0 = (3, 0.0, 0)
harmonic4_0 = (4, 0.0, 0)
harmonic5_0 = (5, 0.0, 0)
harmonic6_0 = (6, 0.0, 0)
harmonic7_0 = (7, 0.0, 0.0)
harmonic8_0 = (8, 0.0, 0)
harmonic9_0 = (9, 0.0, 0)
harmonic10_0 = (10, 0.0, 0)
harmonic11_0= (11, 0.0, 0)
# store harmonics0
harmonics0.append(harmonic2_0)
harmonics0.append(harmonic3_0)
harmonics0.append(harmonic4_0)
harmonics0.append(harmonic5_0)
harmonics0.append(harmonic6_0)
harmonics0.append(harmonic7_0)
harmonics0.append(harmonic8_0)
harmonics0.append(harmonic9_0)
harmonics0.append(harmonic10_0)
harmonics0.append(harmonic11_0)

Stiff = 0
Weak = 1e-3

# --- Scenario reporting to SMT server ---
def report_scenario(label, running=True):
    """Report the current scenario to the SMT server (if running)."""
    payload = json.dumps({"label": label, "running": running}).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8765/scenario",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # Server not running - tests still work standalone

# script directory
FILE_DIR_PATH = Path(__file__).parent

# Path to model file and to compiled model file
model_path = str(FILE_DIR_PATH / "SystemLevel_V3_SMU_V4.tse")
compiled_model_path = model.get_compiled_model_file(model_path)

# Results folder for .mat files (set during test setup)
RESULTS_FOLDER = None

def set_resistor_value(resistor_name, new_r_value):
    """Set resistance of an existing resistor in the schematic."""

    # Model MUST already be loaded
    comp = mdl.get_item(resistor_name, item_type="component")

    if comp is None:
        raise RuntimeError(f"Component '{resistor_name}' not found in schematic")

    # Set resistance
    mdl.set_property_value(
        model.prop(comp, "resistance"),
        float(new_r_value)
    )

    model.save()


def set_inductor_value(inductor_name, new_L_value):
    """Set inductance of an existing inductor in the schematic."""

    # Model MUST already be loaded
    comp = mdl.get_item(inductor_name, item_type="component")

    if comp is None:
        raise RuntimeError(f"Component '{inductor_name}' not found in schematic")

    # Set inductance
    mdl.set_property_value(
        model.prop(comp, "inductance"),
        float(new_L_value)
    )


    model.save()


# Fixture to load schematic, compile and load compiled model to HIL device
@pytest.fixture(scope="module")
def setup():
    global RESULTS_FOLDER

    # Create timestamped results folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    RESULTS_FOLDER = FILE_DIR_PATH / f"Test_Results_{timestamp}"
    RESULTS_FOLDER.mkdir(exist_ok=True)
    print(f"\n  >> Results will be saved to: {RESULTS_FOLDER}")

    model.load(model_path)

    try:
        hw_settings = model.detect_hw_settings()
        vhil_device = False
        report.report_message(f"{hw_settings[0]} C{hw_settings[2]} device is used")
    except Exception:
        vhil_device = True
        model_device = model.get_model_property_value("hil_device")
        model_config = model.get_model_property_value("hil_configuration_id")
        report.report_message(
            f"Virtual HIL device is used. Model is compiled for {model_device} C{model_config}.")
    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)
    # set_inductor_value("Lgrid1",0)

    model.compile()

    hil.load_model(compiled_model_path, vhil_device=vhil_device)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0, harmonics_pu=harmonics)
    hil.set_source_constant_value("V_bat", value=0)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)

    hil.set_scada_input_value("Load_Dist", 0)



    summary_data = []
    yield summary_data

capturedDataBuffer = []
label = []
def pre_cbk(label):
    report_scenario(label)
    global capturedDataBuffer
    # decimation,numberOfChannels,numberOfSamples
    captureSettings = [150, 9, 5e6]
    # triggerType,triggerSource,threshold,edge,triggerOffset
    triggerSettings = ["Forced"]
    # signals for capturing
    channelSettings = ["Ig1","L4","Vc3", "C2","C3","C4","Cdc","Ia3","VLV2"]
    # regular Python list is used for data buffer
    capturedDataBuffer = []
    # Save to timestamped results folder
    output_file = str(RESULTS_FOLDER / f'{label}.mat')
    # start capture process and if everything is ok continue...
    hil.start_capture(
        captureSettings,
        triggerSettings,
        channelSettings,
        dataBuffer=capturedDataBuffer,
        fileName=output_file)

def post_cbk(label):
    hil.stop_capture()
    report_scenario(label, running="paused")

Scenario_data=[(1,10),(2,8),(3,6),(4,5),(5,4),(6,3),(7,2),(8,1),(9,0.5),(10,0.2)]
@pytest.mark.parametrize("Scenario_num,R_fault_value",Scenario_data)

def test_SA_CurrentLimit_Line(setup,Scenario_num,R_fault_value):

    label = f"SA_CurrentLimit_Line_R_{Scenario_num}"

    hil.stop_simulation()

    set_resistor_value("R9", R_fault_value)
    model.compile()


    hil.load_model(compiled_model_path, vhil_device=False)
    hil.set_scada_input_value("Load_Dist", 1)


    hil.start_simulation()
    pre_cbk(label)

    hil.set_source_constant_value("V_bat", value=53)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)

    hil.wait_sec(10)
    hil.set_scada_input_value("Load_Dist", 0)
    hil.wait_sec(2.9952)
    hil.set_scada_input_value("Load_Dist", 1)
    hil.wait_sec(2)
    hil.set_scada_input_value("Load_Dist", 0)
    hil.wait_sec(4)
    hil.set_scada_input_value("Load_Dist", 1)
    hil.wait_sec(5)
    hil.set_scada_input_value("Load_Dist", 0)
    hil.wait_sec(1)
    hil.set_scada_input_value("Load_Dist", 1)

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=50)
    post_cbk(label)
    hil.stop_simulation()

Scenario_data=[(1,10),(2,8),(3,6),(4,5),(5,4),(6,3),(7,2),(8,1),(9,0.5),(10,0.2)]
@pytest.mark.parametrize("Scenario_num,R_fault_value",Scenario_data)
def test_SA_CurrentLimit_Phase(setup,Scenario_num,R_fault_value):

    label = f"SA_CurrentLimit_Phase_R_{Scenario_num}"

    hil.stop_simulation()

    set_resistor_value("R34", R_fault_value)
    set_resistor_value("R9", 2000)
    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 0)



    hil.start_simulation()
    pre_cbk(label)
    hil.set_source_constant_value("V_bat", value=53)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(10)
    hil.set_scada_input_value("Load_Dist", 1)
    hil.wait_sec(3)
    hil.set_scada_input_value("Load_Dist", 0)
    hil.wait_sec(2)
    hil.set_scada_input_value("Load_Dist", 1)
    hil.wait_sec(4)
    hil.set_scada_input_value("Load_Dist", 0)
    hil.wait_sec(7)
    hil.set_scada_input_value("Load_Dist", 1)
    hil.wait_sec(1)
    hil.set_scada_input_value("Load_Dist", 0)
    hil.set_source_constant_value("V_bat", value=50)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    post_cbk(label)
    hil.wait_sec(1)
    hil.stop_simulation()

# connection = 0 ==> Line-to-line  Connection = 1 ===> line-to-neutral

Scenario_data=[(1,harmonics0,1000,Stiff),(2,harmonics0,20,Stiff),
(3,harmonics0,12,Stiff),(4,harmonics0,5,Stiff),(5,harmonics,1000,Stiff),(6,harmonics,20,Stiff),
(7,harmonics,12,Stiff),(8,harmonics,5,Stiff),(9,harmonics0,1000,Weak),(10,harmonics0,20,Weak),
(11,harmonics0,12,Weak),(12,harmonics0,5,Weak),(13,harmonics,1000,Weak),(14,harmonics,20,Weak),
(15,harmonics,12,Weak),(16,harmonics,5,Weak)]

@pytest.mark.parametrize("Scenario_num,harm,rl,Lg",Scenario_data)
def test_GridConnection_lineLoad(setup,Scenario_num,harm,rl,Lg):

    label = f"GridConnection_LineLoad_{Scenario_num}"

    hil.stop_simulation()

    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R34", 2000)
    set_resistor_value("R9", rl)
    set_inductor_value("Lgrid",Lg)
    model.compile()

    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 0)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_source_constant_value("V_bat", value=53)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(10)
    hil.set_source_sine_waveform("Vg_src", rms=120,harmonics_pu = harm)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(30+5)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(4)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(30+5)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(5)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(30+5)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_constant_value("V_bat", value=50)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()


Scenario_data=[(1,harmonics0,1000,Stiff),(2,harmonics0,20,Stiff),
(3,harmonics0,12,Stiff),(4,harmonics0,5,Stiff),(5,harmonics,1000,Stiff),(6,harmonics,20,Stiff),
(7,harmonics,12,Stiff),(8,harmonics,5,Stiff),(9,harmonics0,1000,Weak),(10,harmonics0,20,Weak),
(11,harmonics0,12,Weak),(12,harmonics0,5,Weak),(13,harmonics,1000,Weak),(14,harmonics,20,Weak),
(15,harmonics,12,Weak),(16,harmonics,5,Weak)]

@pytest.mark.parametrize("Scenario_num,harm,rl,Lg",Scenario_data)
def test_GridConnection_PhaseLoad(setup,Scenario_num,harm,rl,Lg):


    label = f"GridConnection_PhaseLoad_{Scenario_num}"

    hil.stop_simulation()

    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", rl*0.5)
    set_inductor_value("Lgrid",Lg)
    # set_inductor_value("Lgrid1",Lg)

    model.compile()

    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 1)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_source_constant_value("V_bat", value=53)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(10)
    hil.set_source_sine_waveform("Vg_src", rms=120,harmonics_pu = harm)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(30+5)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(2)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(30+5)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(3)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(30+5)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_constant_value("V_bat", value=50)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

Scenario_data=[(1,harmonics0,Stiff),(2,harmonics,Stiff),(3,harmonics0,Weak),(4,harmonics,Weak)]
@pytest.mark.parametrize("Scenario_num,harm,Lg",Scenario_data)
def test_GC_currentLimit(setup, Scenario_num, harm,Lg):

    label = f"GC_currentlimit_{Scenario_num}"
    hil.stop_simulation()
    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",Lg)
    # set_inductor_value("Lgrid1",Lg)

    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 1)

    hil.prepare_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0, harmonics_pu=harm)

    hil.start_simulation()

    pre_cbk(label)
    hil.set_source_constant_value("V_bat", value=53)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(10)
    hil.set_source_sine_waveform("Vg_src", rms=120,harmonics_pu = harm)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(20+15)
    hil.set_source_sine_waveform("Vg_src", rms=115)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=120)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=110)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=120)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=105)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=120)
    hil.wait_sec(2+15)
    hil.set_source_sine_waveform("Vg_src", rms=100)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=120)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=130)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=120)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=140)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", rms=120)
    hil.wait_sec(2+15)
    hil.set_source_sine_waveform("Vg_src", frequency=59)
    hil.wait_sec(2+15)
    hil.set_source_sine_waveform("Vg_src", frequency=61)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src", frequency=60)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=10)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=0)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=20)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=0)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=30)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=0)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=40)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=0)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=50)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=0)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=60)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=0)
    hil.wait_sec(2)
    hil.set_source_sine_waveform("Vg_src",phase=70)
    hil.wait_sec(2+15)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(2)
    hil.set_source_constant_value("V_bat", value=50)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

Scenario_data=[(1,harmonics0,Stiff,2),(4,harmonics0,Stiff,3),(5,harmonics0,Stiff,4),(6,harmonics0,Weak,0),(7,harmonics0,Weak,1),(8,harmonics0,Weak,2),(9,harmonics0,Weak,3),(10,harmonics0,Weak,4)]#(1,harmonics0,Stiff,0),(2,harmonics0,Stiff,1),
@pytest.mark.parametrize("Scenario_num,harm,Lg,Td",Scenario_data)
def test_Startup1(setup, Scenario_num, harm,Lg,Td):

    label = f"Startup_GC_Bat_first_{Scenario_num}"
    hil.stop_simulation()
    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R9", 20)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",Lg)
    # set_inductor_value("Lgrid1",Lg)

    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 0)

    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0, harmonics_pu=harm)
    hil.set_source_constant_value("V_bat", value=0)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 0)

    hil.start_simulation()

    pre_cbk(label)
    hil.set_source_constant_value("V_bat", value=53)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(Td)
    hil.set_source_sine_waveform("Vg_src", rms=120,harmonics_pu = harm)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(30)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()


# Scenario_data=[(1,harmonics0,Stiff)]
# @pytest.mark.parametrize("Scenario_num,harm,Lg",Scenario_data)
# def test_Startup2(setup, Scenario_num, harm,Lg):

#     label = f"Startup_FirstGrid_Then_Batt_{Scenario_num}"

#     hil.stop_simulation()
#     set_resistor_value("R5", 2000)
#     set_resistor_value("R6", 2000)
#     set_resistor_value("R9", 2000)
#     set_resistor_value("R34", 2000)
#     set_inductor_value("Lgrid",Lg)
#     set_inductor_value("Lgrid1",Lg)

#     model.compile()
#     hil.load_model(compiled_model_path, vhil_device=False)

#     hil.set_scada_input_value("Load_Dist", 1)

#     pre_cbk(label)
#     hil.prepare_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0, harmonics_pu=harm)
#     hil.set_source_constant_value("V_bat", value=0)
#     hil.start_simulation()

#     hil.set_source_sine_waveform("Vg_src", rms=120,harmonics_pu = harm)
#     hil.set_scada_input_value("Grid_avai", 1)
#     hil.wait_sec(1)
#     hil.set_source_constant_value("V_bat", value=53)

#     hil.wait_sec(50)
#     post_cbk(label)
#     hil.stop_simulation()

##### ****************************** DAB Scenarios ****************************** ###
V_bat_th_L = 51
V_bat_th_H = 54

# Test scenarios for 1.1, 1.2, and 1.3
Scenario_data=[(1,0,(V_bat_th_L-2),0),(2,0,(V_bat_th_L-2)*1.05,0),(3,0,(V_bat_th_L-2)*0.95,0),(4,120,(V_bat_th_L-2),0),(5,120,(V_bat_th_L-2),2),(6,120,(V_bat_th_L-2),5),(7,120,(V_bat_th_L-2),12),(8,120,(V_bat_th_L-2)*1.05,0),(9,120,(V_bat_th_L-2)*1.05,2),(10,120,(V_bat_th_L-2)*1.05,5),(11,120,(V_bat_th_L-2)*0.95,0),(12,120,(V_bat_th_L-2)*0.95,2),(13,120,(V_bat_th_L-2)*0.95,5),
                (14,120,(V_bat_th_L-10),0),(15,120,(V_bat_th_L-10),2),(16,120,(V_bat_th_L-10),5),(17,120,(V_bat_th_L-10)*0.8,0),(18,120,(V_bat_th_L-10)*0.8,2),(19,120,(V_bat_th_L-10)*0.8,5)]

@pytest.mark.parametrize("Scenario_num,Vgrid,Vbatery,Delay",Scenario_data)

def test_DAB_Startup(setup, Scenario_num, Vgrid,Vbatery,Delay):

    label = f"Startup__DAB_Normal_{Scenario_num}"
    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)
    # #set_inductor_value("Lgrid1",Lg)

    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)


    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=Vbatery)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.set_source_sine_waveform("Vg_src", rms=Vgrid, frequency=60, phase=0, harmonics_pu=harmonics0)
    hil.wait_sec(Delay)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(20)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(10)


# Test scenarios for 1.4
Scenario_data=[(1,1),(2,3),(3,5),(4,7)]

@pytest.mark.parametrize("Scenario_num,Delay",Scenario_data)

def test_DAB_Startup_1_4(setup, Scenario_num, Delay):

    label = f"Startup__DAB_Normal_1_4_{Scenario_num}"

    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)

    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)


    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=53)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.set_source_sine_waveform("Vg_src", rms=120, frequency=60, phase=0, harmonics_pu=harmonics0)
    hil.wait_sec(Delay)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(10)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(10)


# Test scenarios for 1.5 , 1.6, 1.7,1.8
# Scenario #, Grid_avai_stat, ChargMos_stat, DisChrgMos_stat
Scenario_data=[(1,0,0,1),(2,0,1,0),(3,1,0,1),(4,1,1,0)]

@pytest.mark.parametrize("Scenario_num,Grid_avai,ChargMos_stat,DisChrgMos_stat",Scenario_data)

def test_DAB_Startup_MOS(setup, Scenario_num, Grid_avai, ChargMos_stat, DisChrgMos_stat):

    label = f"Startup__DAB_Normal_MOS_{Scenario_num}"

    set_resistor_value("R5", 4)
    set_resistor_value("R6", 4)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)

    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)


    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=53)



    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("Grid_avai", Grid_avai)
    hil.set_source_sine_waveform("Vg_src", rms=120, frequency=60, phase=0, harmonics_pu=harmonics0)
    hil.wait_sec(2)
    hil.set_scada_input_value("ChrgMos", ChargMos_stat)
    hil.set_scada_input_value("DisChrgMos", DisChrgMos_stat)
    hil.wait_sec(30)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(10)

# Test scenarios for 2.1
#  10%, 30%, 50%, 70%, 90%, 100%
Scenario_data=[(1,76.8,6.23),(2,25.6,4.73),(3,15.36,9.216),(4,10.97,12.13),(5,8.53,17.72),(6,7.68,23.04)]#
@pytest.mark.parametrize("Scenario_num,Rload1,R_sw",Scenario_data)
def test_DAB_SA_SS_2_1(setup, Scenario_num, Rload1,R_sw):

    label = f"test_DAB_SA_SS_2_1_{Scenario_num}"

    hil.stop_simulation()
    set_resistor_value("R5", Rload1*0.5)
    set_resistor_value("R6", Rload1*0.5)
    set_resistor_value("R9", R_sw)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)
    # set_inductor_value("Lgrid1",Lg)
    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 1)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=53)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(20)
    hil.set_scada_input_value("Load_Dist", 0)
    hil.wait_sec(20)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(20)


# Test scenarios for 2.3
#  10%, 30%, 50%, 70%, 90%, 100% , 125%
Scenario_data=[(1,76.8),(2,25.6),(3,15.36),(4,10.97),(5,8.53),(6,7.68),(6,5.76)]
@pytest.mark.parametrize("Scenario_num,R_sw",Scenario_data)
def test_DAB_SA_SS_2_3(setup, Scenario_num,R_sw):

    label = f"test_DAB_SA_SS_2_3_{Scenario_num}"

    hil.stop_simulation()
    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R9", R_sw)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)
    # set_inductor_value("Lgrid1",Lg)
    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 0)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=53)



    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(20)
    hil.set_scada_input_value("Load_Dist", 1)
    hil.wait_sec(20)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)


# Test scenarios for 2.4
#  10%, 30%, 50%, 70%, 90%, 100% , 125%
Scenario_data=[(1,76.8),(2,25.6),(3,15.36),(4,10.97),(5,8.53),(6,7.68),(6,5.76)]
@pytest.mark.parametrize("Scenario_num,R_sw",Scenario_data)
def test_DAB_SA_SS_2_4(setup, Scenario_num,R_sw):

    label = f"test_DAB_SA_SS_2_4_{Scenario_num}"

    hil.stop_simulation()
    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R9", R_sw)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)
    # set_inductor_value("Lgrid1",Lg)
    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Load_Dist", 1)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=53)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(20)
    hil.set_scada_input_value("Load_Dist", 0)
    hil.wait_sec(20)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)

# Test scenarios for 2.5
#  10%, 30%, 50%, 70%, 90%, 100% , 125%
Scenario_data=[(1,57.6,14.4,0.1),(2,57.6,14.4,0.2)]
@pytest.mark.parametrize("Scenario_num,Rload,R_sw,Delay",Scenario_data)
def test_DAB_SA_SS_2_5(setup, Scenario_num,Rload,R_sw,Delay):

    label = f"test_DAB_SA_SS_2_5_{Scenario_num}"
    hil.stop_simulation()
    set_resistor_value("R5", Rload*0.5)
    set_resistor_value("R6", Rload*0.5)
    set_resistor_value("R9", R_sw)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)
    # set_inductor_value("Lgrid1",Lg)
    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 1)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=53)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(20)
    hil.set_scada_input_value("Load_Dist", 0)
    hil.wait_sec(Delay)
    hil.set_scada_input_value("Load_Dist", 1)
    hil.wait_sec(Delay)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)


# Test scenarios for 2.7
#  10%, 30%, 50%, 70%, 90%, 100% , 125%
Scenario_data=[(1,7.68),(2,5.76)]
@pytest.mark.parametrize("Scenario_num,Rload",Scenario_data)
def test_DAB_SA_SS_2_7(setup, Scenario_num,Rload):

    label = f"test_DAB_SA_SS_2_7_{Scenario_num}"
    hil.stop_simulation()
    set_resistor_value("R5", Rload*0.5)
    set_resistor_value("R6", Rload*0.5)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)
    # set_inductor_value("Lgrid1",Lg)
    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 0)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_sine_waveform("Vg_src", rms=120, frequency=60, phase=0)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=53)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(5)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(30)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(20)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)

# Test scenarios for 2.8
#  10%, 30%, 50%, 70%, 90%, 100% , 125%
Scenario_data=[(1,10)]
@pytest.mark.parametrize("Scenario_num,Rload",Scenario_data)
def test_DAB_SA_SS_2_8(setup, Scenario_num,Rload):

    label = f"test_DAB_SA_SS_2_8_{Scenario_num}"
    hil.stop_simulation()
    set_resistor_value("R5", Rload*0.5)
    set_resistor_value("R6", Rload*0.5)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)
    # set_inductor_value("Lgrid1",Lg)
    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 0)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_sine_waveform("Vg_src", rms=120, frequency=60, phase=0)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=40)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(2)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(0.5)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.wait_sec(0.5)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(0.5)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.wait_sec(0.5)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(0.5)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.wait_sec(0.5)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(0.5)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)

# Test scenarios for 3.2
#  10%, 30%, 50%, 70%, 90%, 100% , 125%
Scenario_data=[(1,15,V_bat_th_L-4),(2,15,V_bat_th_L-10)]
@pytest.mark.parametrize("Scenario_num,Rload,Vbat_new",Scenario_data)
def test_DAB_Mode_Tran_3_2(setup, Scenario_num,Rload,Vbat_new):

    label = f"test_DAB_Mode_Tran_3_2_{Scenario_num}"
    hil.stop_simulation()
    set_resistor_value("R5", Rload*0.5)
    set_resistor_value("R6", Rload*0.5)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)

    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 1)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=53)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(20)
    hil.set_source_constant_value("V_bat", value=Vbat_new)
    hil.wait_sec(30)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)

# Test scenarios for 3.3
Scenario_data=[(1,1.3,V_bat_th_L-4,V_bat_th_L+2),(2,1.3,V_bat_th_L-10,V_bat_th_L+2),(3,1.3,V_bat_th_L-4,V_bat_th_L+5),(4,1.3,V_bat_th_L-10,V_bat_th_L+5),
                (5,1,V_bat_th_L-4,V_bat_th_L+2),(6,1,V_bat_th_L-10,V_bat_th_L+2),(7,1,V_bat_th_L-4,V_bat_th_L+5),(8,1,V_bat_th_L-10,V_bat_th_L+5),
                (9,0.5,V_bat_th_L-4,V_bat_th_L+2),(10,0.5,V_bat_th_L-10,V_bat_th_L+2),(11,0.5,V_bat_th_L-4,V_bat_th_L+5),(12,0.5,V_bat_th_L-10,V_bat_th_L+5)]
@pytest.mark.parametrize("Scenario_num,Xs,Vbat_new,Vbat_new_H",Scenario_data)
def test_DAB_Mode_Tran_3_3(setup, Scenario_num, Xs,Vbat_new,Vbat_new_H):

    label = f"test_DAB_Mode_Tran_3_3_{Scenario_num}"
    hil.stop_simulation()
    set_resistor_value("R5", 15*0.5)
    set_resistor_value("R6", 15*0.5)
    set_resistor_value("R9", 2000)
    set_resistor_value("R34", 2000)
    set_inductor_value("Lgrid",0)

    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 1)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=53)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.wait_sec(5)
    hil.set_source_constant_value("V_bat", value=Vbat_new)
    hil.wait_sec(Xs)
    hil.set_source_constant_value("V_bat", value=Vbat_new_H)
    hil.wait_sec(Xs)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)

# Test scenarios for 3.4
Scenario_data=[(1)]
@pytest.mark.parametrize("Scenario_num",Scenario_data)
def test_DAB_Mode_Tran_3_4(setup, Scenario_num):

    label = f"test_DAB_Mode_Tran_3_4_{Scenario_num}"


    hil.set_scada_input_value("Load_Dist", 1)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.set_source_sine_waveform("Vg_src", rms=120, frequency=60, phase=0)
    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_constant_value("V_bat", value=10)


    hil.start_simulation()

    pre_cbk(label)
    hil.set_scada_input_value("ChrgMos", 1)
    hil.set_scada_input_value("DisChrgMos", 1)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(1)
    hil.set_scada_input_value("Grid_avai", 0)
    hil.wait_sec(3)
    hil.set_scada_input_value("Grid_avai", 1)
    hil.wait_sec(20)
    post_cbk(label)

    hil.wait_sec(1)
    hil.stop_simulation()

    hil.set_scada_input_value("ChrgMos", 0)
    hil.set_scada_input_value("DisChrgMos", 0)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0)
    hil.set_scada_input_value("Grid_avai", 0)
