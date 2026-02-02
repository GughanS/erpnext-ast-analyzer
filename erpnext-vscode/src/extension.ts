import * as vscode from 'vscode';
import * as path from 'path';
import { spawn } from 'child_process';

//  CONFIGURATION: Correct Absolute Paths (Matches your working setup)
// We use absolute paths because relative calculation is unreliable during debugging
const TOOL_PATH = 'D:\\Internship-Obsidian-Vault\\erpnext-ast-analyzer';
const PYTHON_CMD = 'D:\\Internship-Obsidian-Vault\\erpnext-ast-analyzer\\.venv\\Scripts\\python.exe';

export function activate(context: vscode.ExtensionContext) {
    console.log(' ERPNext AST Analyzer extension is now active!');

    // Command 1: Index Code
    let indexDisposable = vscode.commands.registerCommand('erpnext-analyzer.index', async () => {
        // Suggest the controllers path as default since it's commonly needed
        const targetPath = await vscode.window.showInputBox({
            placeHolder: 'Enter full path to folder/file',
            value: 'D:\\Internship-Obsidian-Vault\\erpnext\\erpnext\\accounts', 
            prompt: 'Path to Index (e.g. Controllers, Stock, Accounts)'
        });

        if (targetPath) {
            runPythonTool('index', targetPath);
        }
    });

    // Command 2: Ask Logic
    let askDisposable = vscode.commands.registerCommand('erpnext-analyzer.ask', async () => {
        const query = await vscode.window.showInputBox({
            placeHolder: 'e.g., How does stock update logic work?',
            prompt: 'Ask the ERPNext Knowledge Base'
        });

        if (query) {
            runPythonTool('ask', query);
        }
    });

    // Command 3: Migrate to Go (Restored functionality)
    let migrateDisposable = vscode.commands.registerCommand('erpnext-analyzer.migrate', async () => {
        const query = await vscode.window.showInputBox({
            placeHolder: 'e.g., Convert on_submit to Go',
            prompt: 'Generate Microservice Code'
        });

        if (query) {
            runPythonTool('migrate', query);
        }
    });

    context.subscriptions.push(indexDisposable, askDisposable, migrateDisposable);
}

function runPythonTool(command: string, arg: string) {
    const outputChannel = vscode.window.createOutputChannel("ERPNext AI");
    outputChannel.clear();
    outputChannel.show(true); 
    
    outputChannel.appendLine(` Preparing to run: ${command}`);
    outputChannel.appendLine(` Working Directory: ${TOOL_PATH}`);
    outputChannel.appendLine(` Python Path: ${PYTHON_CMD}`);
    outputChannel.appendLine(` Arguments: "${arg}"`);
    outputChannel.appendLine("----------------------------------------\n");

    const cliPath = path.join(TOOL_PATH, 'cli.py');
    
    // Spawn process with unbuffered output (-u)
    // shell: false prevents Windows CMD string parsing errors
    const pythonProcess = spawn(PYTHON_CMD, ['-u', cliPath, command, arg], {
        cwd: TOOL_PATH,
        env: { 
            ...process.env,
            PYTHONIOENCODING: 'utf-8' 
        },
        shell: false 
    });

    pythonProcess.stdout.on('data', (data) => {
        outputChannel.append(data.toString());
    });

    pythonProcess.stderr.on('data', (data) => {
        const text = data.toString();
        // Ignore Google grpc warnings to keep UI clean
        if (!text.includes("ALTS creds ignored")) {
            outputChannel.append(`[LOG] ${text}`);
        }
    });

    pythonProcess.on('error', (err: Error) => {
        vscode.window.showErrorMessage(`Execution Failed: ${err.message}`);
        outputChannel.appendLine(`\n PROCESS ERROR: ${err.message}`);
    });

    pythonProcess.on('close', (code: number) => {
        outputChannel.appendLine(`\n----------------------------------------`);
        if (code === 0) {
            outputChannel.appendLine(` Process finished successfully.`);
        } else {
            outputChannel.appendLine(` Process exited with code ${code}`);
        }
    });
}

export function deactivate() {}