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
class LexError extends Error {}
class ParseError extends Error {}

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
            throw new LexError(`Unexpected character at ${pos}: ${source[pos]}`);
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
        throw new ParseError(`Expected ${type}, found ${this.current.type}`);
    }
    
    getPrecedence(token) {
        return this.precedences[token.type] || 0;
    }
    
    parse() {
        const node = this.expression(0);
        if (this.current.type !== 'EOF') {
            throw new ParseError(`Unconsumed token: ${this.current.type}`);
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
        throw new ParseError(`Unexpected token: ${token.type} (${token.value})`);
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
        throw new ParseError(`Unexpected infix token: ${token.type}`);
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
const outAst = document.getElementById('demo-output-ast');
const outTrace = document.getElementById('demo-output-trace');
const tabBtns = document.querySelectorAll('.tab-btn');

if (compilerCard && demoView) {
    compilerCard.addEventListener('click', () => {
        grid.classList.add('hidden');
        demoView.classList.remove('hidden');
        // Small delay to allow display:block to apply before scrolling
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
            
            if (target === 'ast') {
                outAst.parentElement.classList.remove('hidden');
                outTrace.parentElement.classList.add('hidden');
                outAst.style.display = 'block';
                outTrace.style.display = 'none';
            } else {
                outTrace.parentElement.classList.remove('hidden');
                outAst.parentElement.classList.add('hidden');
                outTrace.style.display = 'block';
                outAst.style.display = 'none';
            }
        });
    });

    runBtn.addEventListener('click', runCompiler);
}

function runCompiler() {
    try {
        const source = inputEl.value;
        const contextStr = contextEl.value;
        let context = {};
        
        try {
            context = JSON.parse(contextStr);
        } catch (e) {
            outAst.textContent = `Context JSON Parse Error: ${e.message}`;
            outTrace.textContent = `Context JSON Parse Error: ${e.message}`;
            return;
        }
        
        const tokens = tokenize(source);
        const parser = new PrattParser(tokens);
        const ast = parser.parse();
        
        const { result, trace } = executeAst(ast, context);
        
        outAst.textContent = JSON.stringify(ast, null, 2);
        
        const traceOutput = {
            final_result: result,
            execution_trace: trace
        };
        outTrace.textContent = JSON.stringify(traceOutput, null, 2);
        
    } catch (e) {
        outAst.textContent = `Error: ${e.message}`;
        outTrace.textContent = `Error: ${e.message}`;
    }
}

