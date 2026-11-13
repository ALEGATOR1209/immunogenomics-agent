Perform the task presented below.

Work in the current directory. The input data is in data/ (read-only). Put everything you hand in into the outputs/ directory: only its contents are collected when you finish, and everything else is discarded.

You may work in Python or R, or with any other tools available in the environment: for example a Jupyter notebook (Python or R kernel), a Python script or an R script. Both languages come with common single-cell and immune-repertoire packages installed (Python: scanpy, scirpy, muon; R: Seurat, scRepertoire, immunarch and the Immcantation packages alakazam, shazam, scoper and tigger). Whatever you choose, outputs/ must contain the code that, run from the current directory from start to finish, reproduces outputs/output.json. Keep outputs/ to that code, output.json and small supporting files such as figures or short tables; don't save large intermediate data objects there.

Build the code in outputs/ incrementally as you work: add each step as soon as you've verified it, rather than exploring ad hoc (e.g. one-off scripts or shell commands) and only transcribing the final code at the end. Reconstructing everything afterward wastes the exploration work you already did and risks the code drifting from what you actually verified — variables, filters, or intermediate values can subtly change between the throwaway version and the retyped one.

Build outputs/output.json incrementally too: as soon as you've computed and verified an individual field's value, write it into outputs/output.json immediately — don't wait until every field is done to write the file once at the end. Leave fields you haven't gotten to yet at their placeholder value from the format shown below. If your session ends early for any reason before you finish everything, a partial outputs/output.json with some fields already filled in correctly still earns credit for those fields — an output.json that doesn't exist yet because you were saving it for last earns nothing at all, even if you had already worked out most of the answers.

Do not write the entire pipeline in one go and then debug it as a whole. If a step fails (syntax error, wrong column name, wrong API call), fix that specific problem in place — do not delete the whole file and rewrite the entire pipeline from scratch. Rewriting from scratch after every small mistake repeatedly burns your context budget on regenerating code that was already correct, and can leave you unable to finish the task.

Before finishing, run your code from start to finish (e.g. `jupyter nbconvert --to notebook --execute --inplace outputs/task.ipynb`, `python outputs/analysis.py` or `Rscript outputs/analysis.R`) to confirm it actually runs top-to-bottom and reproduces outputs/output.json — don't just trust that the code you wrote matches whatever ad hoc exploration originally produced output.json.

When inspecting data, avoid printing large amounts of output (e.g. every row of a table or every entry of a long list) — filter, sample, or summarize instead. Large tool outputs consume your available context and can leave you unable to finish the task.

If any of your available skills looks relevant to this task, you must invoke the Skill tool to load its full content before writing any code. A skill's short description only tells you that it exists and roughly when to use it — not the specific APIs, function calls, or conventions it documents. Recognizing that a skill applies is not enough by itself; load it before you start.

Task: <TASK>

Save output in outputs/output.json in EXACTLY this format:

<OUTPUT_FORMAT>
