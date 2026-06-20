// Initialize Lucide Icons
lucide.createIcons();

// Card Hover Glow Effect
const handleOnMouseMove = e => {
    const { currentTarget: target } = e;
    
    const rect = target.getBoundingClientRect(),
          x = e.clientX - rect.left,
          y = e.clientY - rect.top;
          
    target.style.setProperty("--mouse-x", `${x}px`);
    target.style.setProperty("--mouse-y", `${y}px`);
};

for (const card of document.querySelectorAll(".card")) {
    card.onmousemove = e => handleOnMouseMove(e);
}

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;
        
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Intersection Observer for fade-in animations on scroll
const observerOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.1
};

const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animationPlayState = 'running';
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Pause animation initially for elements below the fold
document.addEventListener('DOMContentLoaded', () => {
    const animatedElements = document.querySelectorAll('.fade-in-up');
    
    animatedElements.forEach(el => {
        const rect = el.getBoundingClientRect();
        // If element is below viewport, pause its animation until scrolled into view
        if (rect.top > window.innerHeight) {
            el.style.animationPlayState = 'paused';
            observer.observe(el);
        }
    });
});

// --- JS Compiler Implementation (Rules DSL) ---
class LexError extends Error {
    constructor(message, line, col) {
        super(message);
        this.line = line;
        this.col = col;
    }
}
class ParseError extends Error {
    constructor(message, token) {
        super(message);
        this.token = token;
    }
}

function tokenize(source) {
    const spec = [
        ['NUMBER', /^(\d+(\.\d+)?)/],
        ['STRING', /^"([^"]*)"/],
        ['AND', /^\b(?i:and)\b/i],
        ['OR', /^\b(?i:or)\b/i],
        ['NOT', /^\b(?i:not)\b/i],
        ['IF', /^\b(?i:if)\b/i],
        ['THEN', /^\b(?i:then)\b/i],
        ['TRUE', /^\b(?i:true)\b/i],
        ['FALSE', /^\b(?i:false)\b/i],
        ['EQ', /^==/],
        ['NEQ', /^!=/],
        ['GTE', /^>=/],
        ['LTE', /^<=/],
        ['GT', /^>/],
        ['LT', /^</],
        ['LPAREN', /^\(/],
        ['RPAREN', /^\)/],
        ['IDENT', /^[a-zA-Z_]\w*/],
        ['WS', /^\s+/]
    ];
    
    let pos = 0;
    const tokens = [];
    
    while (pos < source.length) {
        let match = null;
        let matchedType = null;
        
        const substr = source.slice(pos);
        
        for (const [type, regex] of spec) {
            match = regex.exec(substr);
            if (match) {
                matchedType = type;
                break;
            }
        }
        
        if (!match) {
            throw new LexError(`Unexpected character: '${source[pos]}'`, 1, pos + 1);
        }
        
        if (matchedType !== 'WS') {
            tokens.push({ type: matchedType, value: match[0], line: 1, col: pos });
        }
        
        pos += match[0].length;
    }
    tokens.push({ type: 'EOF', value: null, line: 1, col: pos });
    return tokens;
}

class PrattParser {
    constructor(tokens) {
        this.tokens = tokens;
        this.pos = 0;
        this.current = tokens[0];
        
        this.precedences = {
            'OR': 10, 'AND': 20,
            'EQ': 30, 'NEQ': 30,
            'GT': 40, 'LT': 40, 'GTE': 40, 'LTE': 40
        };
    }
    
    advance() {
        const prev = this.current;
        if (this.pos < this.tokens.length - 1) {
            this.pos++;
            this.current = this.tokens[this.pos];
        }
        return prev;
    }
    
    expect(type) {
        if (this.current.type === type) return this.advance();
        throw new ParseError(`Expected ${type}, found ${this.current.type}`, this.current);
    }
    
    getPrecedence(token) {
        return this.precedences[token.type] || 0;
    }
    
    parse() {
        if (this.current.type === 'EOF') {
            throw new ParseError('Unexpected EOF', this.current);
        }
        const node = this.expression(0);
        if (this.current.type !== 'EOF') {
            throw new ParseError(`Unconsumed token: ${this.current.type}`, this.current);
        }
        return node;
    }
    
    expression(rbp) {
        let token = this.advance();
        let left = this.nud(token);
        
        while (rbp < this.getPrecedence(this.current)) {
            token = this.advance();
            left = this.led(token, left);
        }
        return left;
    }
    
    nud(token) {
        if (token.type === 'NUMBER') return { type: 'literal', value: parseFloat(token.value) };
        if (token.type === 'STRING') return { type: 'literal', value: token.value.replace(/"/g, '') };
        if (token.type === 'TRUE') return { type: 'literal', value: true };
        if (token.type === 'FALSE') return { type: 'literal', value: false };
        if (token.type === 'IDENT') return { type: 'identifier', name: token.value };
        if (token.type === 'NOT') return { type: 'unary_op', operator: 'not', operand: this.expression(50) };
        if (token.type === 'LPAREN') {
            const expr = this.expression(0);
            this.expect('RPAREN');
            return expr;
        }
        if (token.type === 'IF') {
            const condition = this.expression(0);
            this.expect('THEN');
            const action = this.expression(0);
            return { type: 'binary_op', operator: 'if_then', left: condition, right: action };
        }
        throw new ParseError(`Unexpected token: ${token.type} (${token.value})`, token);
    }
    
    led(token, left) {
        const opMap = {
            'AND': 'and', 'OR': 'or', 'EQ': '==', 'NEQ': '!=',
            'GT': '>', 'LT': '<', 'GTE': '>=', 'LTE': '<='
        };
        const op = opMap[token.type];
        if (op) {
            const right = this.expression(this.getPrecedence(token));
            return { type: 'binary_op', operator: op, left, right };
        }
        throw new ParseError(`Unexpected infix token: ${token.type}`, token);
    }
}

function executeAst(node, context) {
    if (!node) return { result: null, trace: null };
    
    if (node.type === 'literal') {
        return { result: node.value, trace: { type: 'literal', value: node.value, result: node.value } };
    }
    if (node.type === 'identifier') {
        const val = context[node.name] !== undefined ? context[node.name] : null;
        return { result: val, trace: { type: 'identifier', value: node.name, result: val } };
    }
    if (node.type === 'unary_op') {
        const { result: val, trace: childTrace } = executeAst(node.operand, context);
        let res = null;
        if (node.operator === 'not') res = !val;
        return { result: res, trace: { type: 'unary_op', value: `not ${val}`, result: res, children: [childTrace] } };
    }
    if (node.type === 'binary_op') {
        if (node.operator === 'if_then') {
            const { result: condRes, trace: condTrace } = executeAst(node.left, context);
            if (condRes) {
                const { result: actRes, trace: actTrace } = executeAst(node.right, context);
                return { result: actRes, trace: { type: 'if_then', value: 'condition=True', result: actRes, children: [condTrace, actTrace] } };
            } else {
                return { result: null, trace: { type: 'if_then', value: 'condition=False', result: null, children: [condTrace] } };
            }
        }
        
        const { result: leftRes, trace: leftTrace } = executeAst(node.left, context);
        const { result: rightRes, trace: rightTrace } = executeAst(node.right, context);
        
        let res = null;
        switch (node.operator) {
            case '==': res = leftRes == rightRes; break;
            case '!=': res = leftRes != rightRes; break;
            case '>': res = leftRes > rightRes; break;
            case '<': res = leftRes < rightRes; break;
            case '>=': res = leftRes >= rightRes; break;
            case '<=': res = leftRes <= rightRes; break;
            case 'and': res = leftRes && rightRes; break;
            case 'or': res = leftRes || rightRes; break;
        }
        
        return { result: res, trace: { type: 'binary_op', value: `${leftRes} ${node.operator} ${rightRes}`, result: res, children: [leftTrace, rightTrace] } };
    }
    throw new Error(`Unknown node type: ${node.type}`);
}

// --- Demo UI Interactions ---
const compilerCard = document.getElementById('compiler-card');
const grid = document.getElementById('showcases-grid');
const demoView = document.getElementById('compiler-demo');
const backBtn = document.getElementById('demo-back-btn');
const runBtn = document.getElementById('demo-run-btn');
const inputEl = document.getElementById('demo-input');
const contextEl = document.getElementById('demo-context');

const outTokens = document.getElementById('demo-output-tokens');
const outAst = document.getElementById('demo-output-ast');
const outTree = document.getElementById('demo-output-tree');
const outTrace = document.getElementById('demo-output-trace');
const errorPanel = document.getElementById('demo-error-panel');
const resultBadge = document.getElementById('demo-result-badge');
const statsBar = document.getElementById('demo-stats');

const tabBtns = document.querySelectorAll('.tab-btn');
const presetBtns = document.querySelectorAll('.preset-btn');

// AST Visual Tree Renderer
function renderASTVisual(node, prefix = "", isLeft = true) {
    if (!node) return "";
    let result = "";
    
    // Node Representation
    let nodeStr = "";
    if (node.type === "literal") nodeStr = node.value;
    else if (node.type === "identifier") nodeStr = node.name;
    else if (node.type === "unary_op") nodeStr = node.operator;
    else if (node.type === "binary_op") nodeStr = node.operator === "if_then" ? "IF...THEN" : node.operator;
    
    result += prefix + (isLeft ? "├── " : "└── ") + nodeStr + "\n";
    
    // Children
    if (node.type === "unary_op") {
        result += renderASTVisual(node.operand, prefix + (isLeft ? "│   " : "    "), false);
    } else if (node.type === "binary_op") {
        result += renderASTVisual(node.left, prefix + (isLeft ? "│   " : "    "), true);
        result += renderASTVisual(node.right, prefix + (isLeft ? "│   " : "    "), false);
    }
    
    return result;
}

// Node counter
function countNodes(node) {
    if (!node) return 0;
    if (node.type === "literal" || node.type === "identifier") return 1;
    if (node.type === "unary_op") return 1 + countNodes(node.operand);
    if (node.type === "binary_op") return 1 + countNodes(node.left) + countNodes(node.right);
    return 1;
}

if (compilerCard && demoView) {
    compilerCard.addEventListener('click', () => {
        grid.classList.add('hidden');
        demoView.classList.remove('hidden');
        setTimeout(() => {
            demoView.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 50);
        runCompiler();
    });

    backBtn.addEventListener('click', () => {
        demoView.classList.add('hidden');
        grid.classList.remove('hidden');
        document.getElementById('showcases').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const target = btn.dataset.tab;
            
            [outTokens, outAst, outTree, outTrace].forEach(el => {
                if (el) el.parentElement.classList.add('hidden');
            });
            
            if (target === 'tokens') outTokens.parentElement.classList.remove('hidden');
            if (target === 'ast') outAst.parentElement.classList.remove('hidden');
            if (target === 'tree') outTree.parentElement.classList.remove('hidden');
            if (target === 'trace') outTrace.parentElement.classList.remove('hidden');
        });
    });

    // Presets
    const presets = {
        'adult': {
            dsl: 'IF age > 18 AND status == "active" THEN approved',
            ctx: '{\n  "age": 25,\n  "status": "active",\n  "approved": true\n}'
        },
        'premium': {
            dsl: 'IF customer_type == "premium" OR points >= 1000 THEN discount_applied',
            ctx: '{\n  "customer_type": "standard",\n  "points": 1200,\n  "discount_applied": true\n}'
        },
        'error': {
            dsl: 'IF age > 18 AND THEN',
            ctx: '{\n  "age": 20\n}'
        }
    };

    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const preset = presets[btn.dataset.preset];
            if (preset) {
                inputEl.value = preset.dsl;
                contextEl.value = preset.ctx;
                runCompiler();
            }
        });
    });

    runBtn.addEventListener('click', runCompiler);
}

function runCompiler() {
    errorPanel.classList.add('hidden');
    resultBadge.className = 'result-badge null';
    resultBadge.textContent = 'Result: Computing...';
    
    let t0, t1;
    let tokens = [];
    let astNodesCount = 0;
    
    try {
        const source = inputEl.value;
        const contextStr = contextEl.value;
        let context = {};
        
        try {
            context = JSON.parse(contextStr);
        } catch (e) {
            throw new Error(`Context JSON Parse Error: ${e.message}`);
        }
        
        t0 = performance.now();
        
        // 1. Tokenize
        tokens = tokenize(source);
        outTokens.textContent = JSON.stringify(tokens, null, 2);
        
        // 2. Parse
        const parser = new PrattParser(tokens);
        const ast = parser.parse();
        astNodesCount = countNodes(ast);
        outAst.textContent = JSON.stringify(ast, null, 2);
        
        const visualTree = ast.type === "binary_op" && ast.operator === "if_then" 
            ? "IF...THEN\n" + renderASTVisual(ast.left, "", true) + renderASTVisual(ast.right, "", false)
            : renderASTVisual(ast, "", false);
            
        outTree.textContent = visualTree.trim() || "Empty AST";
        
        // 3. Execute
        const { result, trace } = executeAst(ast, context);
        t1 = performance.now();
        
        const traceOutput = {
            final_result: result,
            execution_trace: trace
        };
        outTrace.textContent = JSON.stringify(traceOutput, null, 2);
        
        // Update Results UI
        if (result === true) {
            resultBadge.className = 'result-badge true';
            resultBadge.innerHTML = '<i data-lucide="check-circle" style="width: 16px; height: 16px;"></i> Result: TRUE';
        } else if (result === false) {
            resultBadge.className = 'result-badge false';
            resultBadge.innerHTML = '<i data-lucide="x-circle" style="width: 16px; height: 16px;"></i> Result: FALSE';
        } else {
            resultBadge.className = 'result-badge null';
            resultBadge.textContent = `Result: ${result}`;
        }
        lucide.createIcons();
        
        statsBar.textContent = `Tokens: ${tokens.length} | AST Nodes: ${astNodesCount} | Time: ${(t1 - t0).toFixed(2)} ms`;
        
    } catch (e) {
        let errorMsg = e.message;
        
        if (e instanceof LexError) {
            errorMsg = `Syntax Error (Lexical)\n\n${e.message}\nLine ${e.line}, Column ${e.col}`;
        } else if (e instanceof ParseError) {
            errorMsg = `Syntax Error (Parsing)\n\n${e.message}`;
            if (e.token) {
                errorMsg += `\nLine ${e.token.line}, Column ${e.token.col}`;
                const lines = inputEl.value.split('\n');
                if (lines.length > 0) {
                    errorMsg += `\n\n${lines[0]}\n${' '.repeat(Math.max(0, e.token.col))}^`;
                }
            }
        }
        
        errorPanel.textContent = errorMsg;
        errorPanel.classList.remove('hidden');
        
        resultBadge.className = 'result-badge false';
        resultBadge.innerHTML = '<i data-lucide="alert-triangle" style="width: 16px; height: 16px;"></i> Compilation Error';
        lucide.createIcons();
        
        outAst.textContent = "";
        outTree.textContent = "";
        outTrace.textContent = "";
        statsBar.textContent = `Tokens: ${tokens.length > 0 ? tokens.length : '?'} | AST Nodes: 0 | Time: N/A`;
    }
}

