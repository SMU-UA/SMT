clc
clear all
close all

% ################################################# Input Folder ######################################  
FolderName=sprintf('Test_Results_2026-03-03_12-42-46');
% #####################################################################################################


ScenarioName = {
    'SA--Line-to-Line Load'
    'SA--Phase-to-Neutral Load'
    'GC/SA Transitions--Clean/Distorted Grid Voltage--Line-to-Line Load'
    'GC/SA Transitions--Clean/Distorted Grid Voltage--Line-to-Neutral Load'
    'GC Current Limit--Clean/Distorted Grid Voltage'
    'Startup: Bat First'
    'Startup DAB Normal'
    'Startup DAB Normal 1.4'
    'Startup DAB Normal MOS'
    'SS operation 2.1'
    'SS operation 2.3'
    'SS operation 2.4'
    'SS operation 2.5'
    'SS operation 2.7'
    'SS operation 2.8'
    'test DAB Mode Tran 3.2'
    'test DAB Mode Tran 3.3'
    'test DAB Mode Tran 3.4'
};

FileNamee = {
    'SA_CurrentLimit_Line_R'
    'SA_CurrentLimit_Phase_R'
    'GridConnection_LineLoad'
    'GridConnection_PhaseLoad'
    'GC_currentlimit'
    '%Startup_GC_Bat_first'
    'Startup__DAB_Normal'
    'Startup__DAB_Normal_1_4'
    'Startup__DAB_Normal_MOS'
     'test_DAB_SA_SS_2_1'
     'test_DAB_SA_SS_2_3'
     'test_DAB_SA_SS_2_4'
     'test_DAB_SA_SS_2_5'
     'test_DAB_SA_SS_2_7'
     'test_DAB_SA_SS_2_8'
     'test_DAB_Mode_Tran_3_2'
     'test_DAB_Mode_Tran_3_3'
     'test_DAB_Mode_Tran_3_4'
};

drives = {'D:\','E:\','F:\','C:\','G:\'};
numScenarios = [19,5,4,6,7,6,2,2,1,2,12,1,5,5,5,5];
% ---------- IEEE figure settings ----------
figWidth  = 3.5*2;    % inches (one column)
figHeight = 5.8*(5/4);    % inches (4 subplots)
labelFont = 9;
tickFont  = 8;
titleFont = 9;
lineW     = 1.1;
idx = 0;


for j = 1:length(ScenarioName)
for s = 1:numScenarios(j)

    % -------- Locate and load MAT file --------
    matFileFound = false;
    for k = 1:numel(drives)
        matFile = fullfile(drives{k},'Users\ELITE\InverterMP\STM',FolderName, sprintf('%s_%d.mat', FileNamee{j},s));
        CSVFile = fullfile(drives{k},'Users\ELITE\InverterMP\STM',FolderName, sprintf('%s_%d.csv', FileNamee{j},s));
        if exist(matFile, 'file')
            load(matFile)
            STM=readtable(CSVFile);
            matFileFound = true;
            break
        end
    end

    if ~matFileFound
        warning('Scenario %d file not found.', s);
        continue
    end

    % -------- Figure per scenario --------
    fig = figure(s+idx);
    set(fig, 'Units','inches', ...
             'Position',[1 1 figWidth figHeight], ...
             'Color','w');

    % -------- Subplot 1 --------
    ax(s+idx).h(1) = subplot(8,1,1);
    plot(time_line, channels_data.Vc3,'b', ...
        'LineWidth', lineW)
    hold on
    plot(time_line, channels_data.Cdc, 'r', ...
        'LineWidth', lineW)
    grid on
    ylabel('$v_c$ (V), $V_{dc}$', 'Interpreter','latex', ...
        'FontSize', labelFont)
    title(sprintf('%s – Scenario %d', ScenarioName{j},s), ...
        'FontName','Times New Roman', ...
        'FontSize', titleFont)

    % -------- Subplot 2 --------
    ax(s+idx).h(2) = subplot(8,1,2);
    plot(time_line, channels_data.Ig1, 'b','LineWidth', lineW)
    hold on
    plot(time_line, channels_data.L4, 'r','LineWidth', lineW)
    grid on
    ylabel('$i_g$ (A)', 'Interpreter','latex', ...
        'FontSize', labelFont)

    % -------- Subplot 3 --------
    ax(s+idx).h(3) = subplot(8,1,3);
    plot(time_line, channels_data.Ia3, 'b','LineWidth', lineW)
    grid on
    ylabel('$I_{bat}$ (A)', 'Interpreter','latex', ...
        'FontSize', labelFont)

    % -------- Subplot 4 --------
    ax(s+idx).h(4) = subplot(8,1,4);
    plot(time_line, channels_data.VLV2,'b', 'LineWidth', lineW)
    grid on
    ylabel('$V_{bat}$ (V)', 'Interpreter','latex', ...
        'FontSize', labelFont)
    xlabel('Time (s)', 'FontSize', labelFont)

    % -------- Subplot 5 --------
    ax(s+idx).h(5) = subplot(8,1,5);
    plot(time_line, channels_data.Cdc,'b', 'LineWidth', lineW)
    grid on
    ylabel('$V_{dc}$ (V)', 'Interpreter','latex', ...
        'FontSize', labelFont)
    xlabel('Time (s)', 'FontSize', labelFont)

    % -------- Subplot 6 --------
    ax(s+idx).h(5) = subplot(8,1,6);
    plot(STM.Time_s_-STM.Time_s_(1), STM.VDC,'b', 'LineWidth', lineW)
    grid on
    ylabel('Vdc SMU', 'Interpreter','latex', ...
        'FontSize', labelFont)
    xlabel('Time (s)', 'FontSize', labelFont)
    % -------- Subplot 7 --------
    ax(s+idx).h(5) = subplot(8,1,7);
    plot(STM.Time_s_-STM.Time_s_(1), STM.FCODE,'b', 'LineWidth', lineW)
    grid on
    ylabel('Inverter Fault', 'Interpreter','latex', ...
        'FontSize', labelFont)
    xlabel('Time (s)', 'FontSize', labelFont)
    % -------- Subplot 8 --------
    ax(s+idx).h(5) = subplot(8,1,8);
    plot(STM.Time_s_-STM.Time_s_(1), STM.FCC,'b', 'LineWidth', lineW)
    grid on
    ylabel('DAB Fault', 'Interpreter','latex', ...
        'FontSize', labelFont)
    xlabel('Time (s)', 'FontSize', labelFont)    
    % -------- Axes formatting --------
    set(ax(s+idx).h, ...
        'FontName','Times New Roman', ...
        'FontSize', tickFont, ...
        'LineWidth', 0.8, ...
        'Box','on')

    linkaxes(ax(s+idx).h, 'x')


% ################################################# Saving files ######################################    
safeName = regexprep(ScenarioName{j}, '[^a-zA-Z0-9]', '_');

exportgraphics(fig, ...
    fullfile('C:\Users\ELITE\InverterMP\STM',FolderName, ...
    sprintf('Scenario_%02d_%s.pdf',s, safeName)), ...
    'ContentType','vector')
savefig(fig, ...
    fullfile('C:\Users\ELITE\InverterMP\STM',FolderName, ...
    sprintf('Scenario_%02d_%s.fig', s, safeName)))
% ######################################################################################################
end
idx=idx+numScenarios(j);
end