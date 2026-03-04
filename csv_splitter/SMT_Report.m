function SMT_Report()
close all
clc
rehash toolboxcache
%SMT_REPORT  GUI tool that splits dashboard CSV and generates IEEE-style
%            reports by combining HIL .mat data with SMT Modbus CSV data.
%
%   Usage:  Run "SMT_Report" in MATLAB.  A GUI will appear:
%     1. Browse for the raw dashboard CSV (from Downloads).
%     2. Browse for the test-results folder (containing .mat files).
%     3. Click "Generate Reports" to split, plot and export.

% ===================== label-to-title mapping ============================
%  FileNameBase : prefix used in the label / .mat filename (without _N)
%  ScenarioName : human-readable title shown on figures
FileNameBase = {
    'SA_CurrentLimit_Line_R'
    'SA_CurrentLimit_Phase_R'
    'GridConnection_LineLoad'
    'GridConnection_PhaseLoad'
    'GC_currentlimit'
    'Startup_GC_Bat_first'
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

% ===================== IEEE figure settings ==============================
figWidth  = 3.5*2;       % inches (two-column)
figHeight = 5.8*(5/4);   % inches
labelFont = 9;
tickFont  = 8;
titleFont = 9;
lineW     = 1.1;

% ===================== build GUI =========================================
hFig = uifigure('Name','SMT Report Generator', ...
    'NumberTitle','off', ...
    'MenuBar','none', ...
    'ToolBar','none', ...
    'Units','pixels', ...
    'Position',[300 200 720 480], ...
    'Resize','on', ...
    'Color',[0.94 0.94 0.94]);

% --- CSV file selection ---
uicontrol(hFig,'Style','text', ...
    'String','1. Dashboard CSV File:', ...
    'Units','normalized','Position',[0.02 0.90 0.25 0.05], ...
    'HorizontalAlignment','left','FontWeight','bold', ...
    'BackgroundColor',[0.94 0.94 0.94]);

hCsvLabel = uicontrol(hFig,'Style','text', ...
    'String','No file selected', ...
    'Units','normalized','Position',[0.02 0.85 0.78 0.05], ...
    'HorizontalAlignment','left', ...
    'BackgroundColor',[1 1 1]);

uicontrol(hFig,'Style','pushbutton', ...
    'String','Browse...', ...
    'Units','normalized','Position',[0.82 0.85 0.16 0.06], ...
    'Callback',@browseCSV);

% --- Results folder selection ---
uicontrol(hFig,'Style','text', ...
    'String','2. Test Results Folder (.mat files):', ...
    'Units','normalized','Position',[0.02 0.78 0.35 0.05], ...
    'HorizontalAlignment','left','FontWeight','bold', ...
    'BackgroundColor',[0.94 0.94 0.94]);

hFolderLabel = uicontrol(hFig,'Style','text', ...
    'String','No folder selected', ...
    'Units','normalized','Position',[0.02 0.73 0.78 0.05], ...
    'HorizontalAlignment','left', ...
    'BackgroundColor',[1 1 1]);

uicontrol(hFig,'Style','pushbutton', ...
    'String','Browse...', ...
    'Units','normalized','Position',[0.82 0.73 0.16 0.06], ...
    'Callback',@browseFolder);

% --- Labels table ---
uicontrol(hFig,'Style','text', ...
    'String','3. Labels Found (excluding Logging...):', ...
    'Units','normalized','Position',[0.02 0.66 0.40 0.05], ...
    'HorizontalAlignment','left','FontWeight','bold', ...
    'BackgroundColor',[0.94 0.94 0.94]);

hTable = uitable(hFig, ...
    'Units','normalized','Position',[0.02 0.20 0.96 0.45], ...
    'ColumnName',{'Label','Rows','MAT Found'}, ...
    'ColumnWidth',{380, 70, 80}, ...
    'RowName',[]);

% --- Generate button ---
hGenBtn = uicontrol(hFig,'Style','pushbutton', ...
    'String','Generate Reports', ...
    'Units','normalized','Position',[0.30 0.06 0.40 0.08], ...
    'FontSize',11,'FontWeight','bold', ...
    'Enable','off', ...
    'Callback',@generateReports);

% --- Status bar ---
hStatus = uicontrol(hFig,'Style','text', ...
    'String','', ...
    'Units','normalized','Position',[0.02 0.00 0.96 0.05], ...
    'HorizontalAlignment','left', ...
    'BackgroundColor',[0.94 0.94 0.94]);

% ===================== shared state ======================================
csvPath   = '';
folderPath = '';
rawTable  = [];
labels    = {};
labelRows = [];

% ===================== callbacks =========================================

    function browseCSV(~,~)
        defaultDir = fullfile(getenv('USERPROFILE'),'Downloads');
        if ~isfolder(defaultDir), defaultDir = pwd; end
        [f,p] = uigetfile({'*.csv','CSV files'},'Select Dashboard CSV', defaultDir);
        figure(hFig);  % bring GUI back to front
        if isequal(f,0), return; end
        csvPath = fullfile(p,f);
        set(hCsvLabel,'String',csvPath);
        loadCSV();
        checkReady();
    end

    function browseFolder(~,~)
        d = uigetdir(pwd,'Select Test Results Folder');
        figure(hFig);  % bring GUI back to front
        if isequal(d,0), return; end
        folderPath = d;
        set(hFolderLabel,'String',folderPath);
        refreshTable();
        checkReady();
    end

    function loadCSV()
        try
            rawTable = readtable(csvPath,'TextType','string');
        catch err
            errordlg(sprintf('Failed to read CSV:\n%s',err.message),'Error');
            rawTable = [];
            return
        end
        if ~any(strcmp(rawTable.Properties.VariableNames,'Label'))
            errordlg('CSV does not contain a "Label" column.','Error');
            rawTable = [];
            return
        end
        % filter out "Logging..."
        mask = strtrim(rawTable.Label) ~= "Logging...";
        filtered = rawTable(mask,:);
        [labels, ~, ic] = unique(strtrim(filtered.Label),'stable');
        labelRows = accumarray(ic,1);
        refreshTable();
        set(hStatus,'String', ...
            sprintf('Loaded %d rows, %d labels (excluding Logging...)', ...
            height(rawTable), numel(labels)));
    end

    function refreshTable()
        if isempty(labels), return; end
        matStatus = repmat("—",numel(labels),1);
        if ~isempty(folderPath)
            for k = 1:numel(labels)
                matFile = fullfile(folderPath, labels{k}+".mat");
                if isfile(matFile)
                    matStatus(k) = "Yes";
                else
                    matStatus(k) = "No";
                end
            end
        end
        set(hTable,'Data',[labels, num2cell(labelRows), cellstr(matStatus)]);
    end

    function checkReady()
        if ~isempty(rawTable) && ~isempty(folderPath)
            set(hGenBtn,'Enable','on');
        else
            set(hGenBtn,'Enable','off');
        end
    end

% ===================== main pipeline =====================================

    function generateReports(~,~)
        set(hGenBtn,'Enable','off');
        set(hStatus,'String','Generating plots...');
        drawnow;

        % --- Step 1: split CSV in memory (no files saved) ---
        mask = strtrim(rawTable.Label) ~= "Logging...";
        filtered = rawTable(mask,:);
        splitLabels = unique(strtrim(filtered.Label),'stable');

        % build a map: label -> table of rows (in memory only)
        csvMap = containers.Map();
        for k = 1:numel(splitLabels)
            lbl = splitLabels{k};
            csvMap(char(lbl)) = filtered(strtrim(filtered.Label)==lbl,:);
        end

        % --- Step 2: plot each scenario ---
        figIdx = 0;
        plotCount = 0;
        skipped = 0;

        for j = 1:numel(FileNameBase)
            base = FileNameBase{j};
            scName = ScenarioName{j};

            % find all scenario numbers for this base from CSV labels
            nums = [];
            for k = 1:numel(splitLabels)
                tok = regexp(splitLabels{k}, ['^' regexptranslate('escape',base) '_(\d+)$'],'tokens');
                if ~isempty(tok)
                    nums(end+1) = str2double(tok{1}{1}); %#ok<AGROW>
                end
            end
            nums = sort(nums);
            if isempty(nums), continue; end

            for s = nums
                matFile = fullfile(folderPath, sprintf('%s_%d.mat',base,s));
                csvKey = sprintf('%s_%d',base,s);

                if ~isfile(matFile)
                    warning('MAT file not found: %s', matFile);
                    skipped = skipped + 1;
                    continue
                end

                set(hStatus,'String', ...
                    sprintf('Plotting %s – Scenario %d ...', scName, s));
                drawnow;

                % load HIL data from .mat
                matData = load(matFile);

                % get SMT data from in-memory map
                hasCSV = csvMap.isKey(csvKey);
                if hasCSV
                    STM = csvMap(csvKey);
                end

                % ---- figure ----
                figIdx = figIdx + 1;
                fig = figure(figIdx);
                set(fig,'Units','inches', ...
                    'Position',[1 1 figWidth figHeight], ...
                    'Color','w');

                nSub = 5;
                if hasCSV, nSub = 8; end

                % subplot 1 — Vc3 & Cdc
                axH(1) = subplot(nSub,1,1);
                plot(matData.time_line, matData.channels_data.Vc3,'b','LineWidth',lineW); hold on
                plot(matData.time_line, matData.channels_data.Cdc,'r','LineWidth',lineW);
                grid on
                ylabel('$v_c$ (V), $V_{dc}$','Interpreter','latex','FontSize',labelFont)
                title(sprintf('%s – Scenario %d', scName, s), ...
                    'FontName','Times New Roman','FontSize',titleFont)

                % subplot 2 — Ig1 & L4
                axH(2) = subplot(nSub,1,2);
                plot(matData.time_line, matData.channels_data.Ig1,'b','LineWidth',lineW); hold on
                plot(matData.time_line, matData.channels_data.L4,'r','LineWidth',lineW);
                grid on
                ylabel('$i_g$ (A)','Interpreter','latex','FontSize',labelFont)

                % subplot 3 — Ia3
                axH(3) = subplot(nSub,1,3);
                plot(matData.time_line, matData.channels_data.Ia3,'b','LineWidth',lineW);
                grid on
                ylabel('$I_{bat}$ (A)','Interpreter','latex','FontSize',labelFont)

                % subplot 4 — VLV2
                axH(4) = subplot(nSub,1,4);
                plot(matData.time_line, matData.channels_data.VLV2,'b','LineWidth',lineW);
                grid on
                ylabel('$V_{bat}$ (V)','Interpreter','latex','FontSize',labelFont)

                % subplot 5 — Cdc
                axH(5) = subplot(nSub,1,5);
                plot(matData.time_line, matData.channels_data.Cdc,'b','LineWidth',lineW);
                grid on
                ylabel('$V_{dc}$ (V)','Interpreter','latex','FontSize',labelFont)

                if hasCSV
                    tCSV = STM.Time_s_ - STM.Time_s_(1);

                    % subplot 6 — VDC (SMT)
                    axH(6) = subplot(nSub,1,6);
                    plot(tCSV, STM.VDC,'b','LineWidth',lineW);
                    grid on
                    ylabel('Vdc SMU','Interpreter','latex','FontSize',labelFont)

                    % subplot 7 — Inverter Fault
                    axH(7) = subplot(nSub,1,7);
                    plot(tCSV, STM.FCODE,'b','LineWidth',lineW);
                    grid on
                    ylabel('Inverter Fault','Interpreter','latex','FontSize',labelFont)

                    % subplot 8 — DAB Fault
                    axH(8) = subplot(nSub,1,8);
                    plot(tCSV, STM.FCC,'b','LineWidth',lineW);
                    grid on
                    ylabel('DAB Fault','Interpreter','latex','FontSize',labelFont)
                end

                xlabel('Time (s)','FontSize',labelFont)

                % axes formatting
                set(axH,'FontName','Times New Roman', ...
                    'FontSize',tickFont, ...
                    'LineWidth',0.8, ...
                    'Box','on')
                linkaxes(axH,'x')

                % ---- export ----
                safeName = regexprep(scName,'[^a-zA-Z0-9]','_');
                exportgraphics(fig, ...
                    fullfile(folderPath, sprintf('Scenario_%02d_%s.pdf',s,safeName)), ...
                    'ContentType','vector');
                savefig(fig, ...
                    fullfile(folderPath, sprintf('Scenario_%02d_%s.fig',s,safeName)));

                plotCount = plotCount + 1;
                clear axH
            end
        end

        set(hStatus,'String', ...
            sprintf('Done!  %d reports generated,  %d skipped (no .mat) — output: %s', ...
            plotCount, skipped, folderPath));
        set(hGenBtn,'Enable','on');
    end

end
