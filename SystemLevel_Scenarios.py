import io
import json
import time
import urllib.request
from pathlib import Path

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
def report_scenario(scenario_num, label=""):
    """Report the current scenario to the SMT server (if running)."""
    payload = json.dumps({"scenario": scenario_num, "label": label}).encode("utf-8")
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
model_path = str(FILE_DIR_PATH / "SystemLevel_V2.tse")
compiled_model_path = model.get_compiled_model_file(model_path)

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

    # Save and compile
    model.save()

    # if model.compile():
    #     print(f"{resistor_name} set to {new_r_value} Ohm and model compiled.")
    # else:
    #     raise RuntimeError("Model compilation failed")
        
def set_inductor_value(inductor_name, new_L_value):
    """Set inductance of an existing inductor in the schematic."""

    # Model MUST already be loaded
    comp = mdl.get_item(inductor_name, item_type="component")

    if comp is None:
        raise RuntimeError(f"Component '{inductor_name}' not found in schematic")

    # Set resistance
    mdl.set_property_value(
        model.prop(comp, "inductance"),
        float(new_L_value)
    )    

    # Save and compile
    model.save()

    # if model.compile():
    #     print(f"{inductor_name} set to {new_L_value} Ohm and model compiled.")
    # else:
    #     raise RuntimeError("Model compilation failed")

    
# Fixture to load schematic, compile and load compiled model to HIL device
@pytest.fixture(scope="module")
def setup():
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
    hil.prepare_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0, harmonics_pu=harmonics)
    hil.set_source_constant_value("V_bat", value=0)

    hil.set_scada_input_value("Load_Dist", 0)


    
    summary_data = []
    yield summary_data
    
capturedDataBuffer = []
label = []
def pre_cbk(label):
    global capturedDataBuffer
    # decimation,numberOfChannels,numberOfSamples
    captureSettings = [150, 9, 5e6]
    # triggerType,triggerSource,threshold,edge,triggerOffset
    triggerSettings = ["Forced"]
    # signals for capturing
    channelSettings = ["Ig1","L4","Vc3", "C2","C3","C4","Cdc","Ia3","VLV2"]
    # regular Python list is used for data buffer
    capturedDataBuffer = []
    # start capture process and if everything is ok continue...
    hil.start_capture(
        captureSettings,
        triggerSettings,
        channelSettings,
        dataBuffer=capturedDataBuffer,
        fileName=str(FILE_DIR_PATH / f'{label}.mat'))

def post_cbk(label):
    hil.stop_capture()
    
Scenario_data=[(1,10),(2,8),(3,6),(4,5),(5,4),(6,3),(7,2),(8,1),(9,0.5),(10,0.2)]
@pytest.mark.parametrize("Scenario_num,R_fault_value",Scenario_data)
                 
def test_SA_CurrentLimit_Line(setup,Scenario_num,R_fault_value):
    
    label = f"SA_CurrentLimit_Line_R_{Scenario_num}"
    report_scenario(Scenario_num, label)

    hil.stop_simulation()
    
    set_resistor_value("R9", R_fault_value)
    model.compile()


    hil.load_model(compiled_model_path, vhil_device=False)
    hil.set_scada_input_value("Load_Dist", 1)

    pre_cbk(label)

    hil.start_simulation()
    hil.set_source_constant_value("V_bat", value=53)
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
    hil.set_source_constant_value("V_bat", value=50)
    post_cbk(label)
    hil.stop_simulation()
    
Scenario_data=[(1,10),(2,8),(3,6),(4,5),(5,4),(6,3),(7,2),(8,1),(9,0.5),(10,0.2)]
@pytest.mark.parametrize("Scenario_num,R_fault_value",Scenario_data)
def test_SA_CurrentLimit_Phase(setup,Scenario_num,R_fault_value):
    
    label = f"SA_CurrentLimit_Phase_R_{Scenario_num}"
    report_scenario(Scenario_num, label)

    hil.stop_simulation()

    set_resistor_value("R34", R_fault_value)
    set_resistor_value("R9", 2000)
    model.compile()
    hil.load_model(compiled_model_path, vhil_device=False)

    hil.set_scada_input_value("Load_Dist", 0)

    pre_cbk(label)

    hil.start_simulation()
    hil.wait_sec(1)
    hil.set_source_constant_value("V_bat", value=53)
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
    post_cbk(label)
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
    report_scenario(Scenario_num, label)

    hil.stop_simulation()

    set_resistor_value("R5", 2000)
    set_resistor_value("R6", 2000)
    set_resistor_value("R34", 2000)
    set_resistor_value("R9", rl)
    set_inductor_value("Lgrid",Lg)
    # set_inductor_value("Lgrid1",Lg)
    model.compile()

    hil.load_model(compiled_model_path, vhil_device=False)
    
    hil.set_scada_input_value("Load_Dist", 0)

    pre_cbk(label)

    hil.start_simulation()
    hil.wait_sec(1)
    hil.set_source_constant_value("V_bat", value=53)
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
    post_cbk(label)
    hil.stop_simulation()


Scenario_data=[(1,harmonics0,1000,Stiff),(2,harmonics0,20,Stiff),
(3,harmonics0,12,Stiff),(4,harmonics0,5,Stiff),(5,harmonics,1000,Stiff),(6,harmonics,20,Stiff),
(7,harmonics,12,Stiff),(8,harmonics,5,Stiff),(9,harmonics0,1000,Weak),(10,harmonics0,20,Weak),
(11,harmonics0,12,Weak),(12,harmonics0,5,Weak),(13,harmonics,1000,Weak),(14,harmonics,20,Weak),
(15,harmonics,12,Weak),(16,harmonics,5,Weak)]

@pytest.mark.parametrize("Scenario_num,harm,rl,Lg",Scenario_data)
def test_GridConnection_PhaseLoad(setup,Scenario_num,harm,rl,Lg):

    
    label = f"GridConnection_PhaseLoad_{Scenario_num}"
    report_scenario(Scenario_num, label)

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

    pre_cbk(label)

    hil.start_simulation()
    hil.wait_sec(1)
    hil.set_source_constant_value("V_bat", value=53)
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
    post_cbk(label)
    hil.stop_simulation()

Scenario_data=[(1,harmonics0,Stiff),(2,harmonics,Stiff),(3,harmonics0,Weak),(4,harmonics,Weak)]
@pytest.mark.parametrize("Scenario_num,harm,Lg",Scenario_data)
def test_GC_currentLimit(setup, Scenario_num, harm,Lg):
    
    label = f"GC_currentlimit_{Scenario_num}"
    report_scenario(Scenario_num, label)

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

    pre_cbk(label)
    hil.prepare_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0, harmonics_pu=harm)

    hil.start_simulation()
    hil.wait_sec(1)
    hil.set_source_constant_value("V_bat", value=53)
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
    post_cbk(label)
    hil.stop_simulation()

Scenario_data=[(1,harmonics0,Stiff,0),(2,harmonics0,Stiff,1),(3,harmonics0,Stiff,2),(4,harmonics0,Stiff,3),(5,harmonics0,Stiff,4),(6,harmonics0,Weak,0),(7,harmonics0,Weak,1),(8,harmonics0,Weak,2),(9,harmonics0,Weak,3),(10,harmonics0,Weak,4)]
@pytest.mark.parametrize("Scenario_num,harm,Lg,Td",Scenario_data)
def test_Startup1(setup, Scenario_num, harm,Lg,Td):
    
    label = f"Startup_GC_Bat_first_{Scenario_num}"
    report_scenario(Scenario_num, label)

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

    pre_cbk(label)
    hil.set_source_sine_waveform("Vg_src", rms=0, frequency=60, phase=0, harmonics_pu=harm)
    hil.set_source_constant_value("V_bat", value=0)
    hil.set_scada_input_value("Grid_avai", 0) 

    hil.start_simulation()
    hil.set_source_constant_value("V_bat", value=53)
    hil.wait_sec(Td)
    hil.set_source_sine_waveform("Vg_src", rms=120,harmonics_pu = harm)
    hil.set_scada_input_value("Grid_avai", 1) 
    hil.wait_sec(30)
    post_cbk(label)
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