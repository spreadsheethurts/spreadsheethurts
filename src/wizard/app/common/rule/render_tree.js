const { JSDOM } = require('jsdom');
const d3 = require('d3');
const process = require('process');

// --- Constants ---
// Styles
const FONT_FAMILY = "monospace";
const GLOBAL_TEXT_COLOR = "#1A1A1A";
const NODE_FONT_SIZE = 12;
const PARSER_FONT_SIZE = 10;
const EDGE_FONT_SIZE = 14;
const BASE_PENWIDTH = 1.0;
const HIGHLIGHT_PENWIDTH_NODE = 3.5;
const HIGHLIGHT_PENWIDTH_EDGE = 3.5;

// Maximum width for value box (only value needs truncation)
const MAX_VALUE_WIDTH = 300;

// Node Colors
const BRANCH_FILLCOLOR = "#d6e4f1";
const BRANCH_PENCOLOR = "#000000";
const BRANCH_HIGHLIGHT_FILLCOLOR = "#FFD700";
const BRANCH_HIGHLIGHT_PENCOLOR = "#000000";

const LEAF_FILLCOLOR = "#a0c4ff";
const LEAF_PENCOLOR = "#000000";
const LEAF_HIGHLIGHT_FILLCOLOR = "#a0c4ff";  // Same as normal (no color change)
const LEAF_HIGHLIGHT_PENCOLOR = "#000000";

const PARSER_FILLCOLOR = "#d6e4f1";
const PARSER_PENCOLOR = "#000000";
const PARSER_HIGHLIGHT_FILLCOLOR = "#d6e4f1";  // Same as normal (no color change)
const PARSER_HIGHLIGHT_PENCOLOR = "#000000";

// Edge Colors
const EDGE_COLOR = "#000000";
const EDGE_HIGHLIGHT_COLOR = "#000000";
const ARROW_COLOR = "#000000";

// Edge Label Colors
const TRUE_LABEL_COLOR = "#00AA00";  // Green for true edge labels
const FALSE_LABEL_COLOR = "#CC0000";  // Red for false edge labels
const CUSTOM_LABEL_COLOR = "#000000";  // Black for custom routing key labels

// Input/Output Box Styling
const IO_BOX_FILLCOLOR = "#fdffb6";
const IO_BOX_PENCOLOR = "#000000";
const IO_BOX_TEXT_COLOR = "#212121";
const INPUT_BOX_HEIGHT = 40;
const OUTPUT_BOX_HEIGHT = 40; // <-- NEW: Output box has same height as input
const INPUT_TO_ROOT_SPACE = 125; // 5x the original distance (25 * 5 = 125)
const LEAF_TO_PARSER_SPACE = 8;
const LEAF_TO_OUTPUT_SPACE = 20; // <-- NEW: Space between leaf/parser and its output

// Dimensions & Layout
const SVG_WIDTH = 1600;
const SVG_HEIGHT = 1200;
const MARGIN = { top: 30, right: 40, bottom: 30, left: 40 };

const MAIN_SHAPE_WIDTH = 200;
const MAIN_SHAPE_HEIGHT = 40;
const PARSER_BOX_HEIGHT = 22;
const EDGE_LABEL_OFFSET_Y = -15;
const EDGE_LABEL_OFFSET_X = 10;




// --- Helper Functions ---
function truncateText(text, maxWidth) {
    const MONO_CHAR_WIDTH = NODE_FONT_SIZE * 0.6; // Same as output calculation
    const ellipsis = '...';
    const ellipsisWidth = ellipsis.length * MONO_CHAR_WIDTH;

    if (text.length * MONO_CHAR_WIDTH <= maxWidth) {
        return text;
    }

    // Calculate how many characters we can keep
    const availableWidth = maxWidth - ellipsisWidth;
    const keepChars = Math.floor(availableWidth / MONO_CHAR_WIDTH);

    if (keepChars <= 1) {
        return ellipsis;
    }

    // Distribute characters evenly on both sides
    const leftChars = Math.ceil(keepChars / 2);
    const rightChars = keepChars - leftChars;

    return text.substring(0, leftChars) + ellipsis + text.substring(text.length - rightChars);
}

function buildHierarchy(nodes, edges) {
    if (!nodes || nodes.length === 0) { console.warn("buildHierarchy: No nodes provided."); return null; }
    const nodeMap = new Map(nodes.map(n => [n.uid, { ...n, children: [] }]));
    const childrenUids = new Set();
    edges.forEach(edge => {
        if (edge.target) childrenUids.add(edge.target);
        const parent = nodeMap.get(edge.source);
        const child = nodeMap.get(edge.target);
        if (parent && child) {
            // Enhanced edge info to support custom routing keys
            const label = edge.label || '';
            child._edge_info = {
                label: label,
                is_true: label.toLowerCase() === "true",
                is_false: label.toLowerCase() === "false",
                is_custom: label.toLowerCase() !== "true" && label.toLowerCase() !== "false"
            };
            parent.children.push(child);
        }
    });
    const roots = nodes.filter(n => !childrenUids.has(n.uid)).map(n => nodeMap.get(n.uid));
    if (roots.length === 1) return roots[0];
    if (roots.length === 0) { console.error("Error: No root node found."); return null; }
    console.error(`Error: Multiple root nodes found (${roots.map(r => r.uid).join(', ')}).`);
    return null;
}

// --- Main Execution ---
try {
    const inputJson = process.argv[2];
    const inputData = JSON.parse(inputJson);

    // --- UPDATED: 'output' is no longer a global variable ---
    const { branches, leaves, edges, highlights, input } = inputData;
    if (!branches || !leaves || !edges || !highlights) {
        console.error("Invalid JSON input: requires 'branches', 'leaves', 'edges', and 'highlights' fields.");
        process.exit(1);
    }

    const nodes = [
        ...branches.map(b => ({ uid: b.uid, label: b.name, leaf: false })),
        ...leaves.map(l => ({ ...l, leaf: true })) // Leaf nodes now carry their own 'output'
    ];

    const highlightUidSet = new Set(highlights);
    const hierarchicalData = buildHierarchy(nodes, edges);

    if (!hierarchicalData) { process.exit(1); }

    const dom = new JSDOM(`<!DOCTYPE html><body></body>`);
    const body = d3.select(dom.window.document.body);
    const svg = body.append('svg')
        .attr('xmlns', 'http://www.w3.org/2000/svg')
        .attr('width', SVG_WIDTH).attr('height', SVG_HEIGHT)
        .attr('font-family', FONT_FAMILY);

    svg.append("defs").append("marker").attr("id", "arrowhead").attr("viewBox", "-0 -5 10 10").attr("refX", 8).attr("refY", 0).attr("orient", "auto").attr("markerWidth", 6).attr("markerHeight", 6).append("svg:path").attr("d", "M 0,-4 L 8,0 L 0,4").attr("fill", ARROW_COLOR);
    svg.append("defs").append("marker").attr("id", "arrowhead-highlight").attr("viewBox", "-0 -5 10 10").attr("refX", 8).attr("refY", 0).attr("orient", "auto").attr("markerWidth", 6).attr("markerHeight", 6).append("svg:path").attr("d", "M 0,-4 L 8,0 L 0,4").attr("fill", EDGE_HIGHLIGHT_COLOR);

    const treeGroup = svg.append('g').attr('class', 'decision-tree');
    const root = d3.hierarchy(hierarchicalData);

    root.sort((a, b) => (a.data._edge_info?.is_true === false ? 0 : 1) - (b.data._edge_info?.is_true === false ? 0 : 1));

    // --- UPDATED: Node size calculation now includes dynamic width based on content ---
    root.each(d => {
        let nodeHeight = MAIN_SHAPE_HEIGHT;
        let nodeWidth = MAIN_SHAPE_WIDTH;

        if (!d.data.leaf) {
            // Branch node - width based on label text
            const MONO_CHAR_WIDTH = NODE_FONT_SIZE * 0.6;
            const labelWidth = d.data.label.length * MONO_CHAR_WIDTH + 20; // Add padding
            nodeWidth = Math.max(MAIN_SHAPE_WIDTH, Math.min(labelWidth, MAIN_SHAPE_WIDTH * 2)); // Cap at 2x original
        } else {
            // Leaf node - width based on maximum of type text and parser text
            const MONO_CHAR_WIDTH = NODE_FONT_SIZE * 0.6;
            const typWidth = (d.data.typ || '').length * MONO_CHAR_WIDTH + 20; // Add padding

            // Calculate parser width if parser exists
            let parserWidth = 0;
            if (d.data.parser) {
                const MONO_CHAR_WIDTH_PARSER = PARSER_FONT_SIZE * 0.6;
                parserWidth = d.data.parser.length * MONO_CHAR_WIDTH_PARSER + 16; // Add padding
            }

            // Use maximum width among type and parser
            const maxContentWidth = Math.max(typWidth, parserWidth);
            nodeWidth = Math.max(MAIN_SHAPE_WIDTH, Math.min(maxContentWidth, MAIN_SHAPE_WIDTH * 2)); // Cap at 2x original

            // Calculate additional height
            if (d.data.parser) {
                nodeHeight += LEAF_TO_PARSER_SPACE + PARSER_BOX_HEIGHT;
            }
            if (d.data.examples && d.data.examples.length > 0) {
                // Examples are stacked with no margin between them
                nodeHeight += d.data.examples.length * INPUT_BOX_HEIGHT;
            }
            if (d.data.output) { // If a leaf has an output, add space for it
                nodeHeight += LEAF_TO_OUTPUT_SPACE + OUTPUT_BOX_HEIGHT;
            }
        }

        d._calculatedHeight = nodeHeight;
        d._calculatedWidth = nodeWidth;
    });

    const treeLayout = d3.tree().nodeSize([d3.max(root.descendants(), d => d._calculatedWidth || MAIN_SHAPE_WIDTH) * 1.1, d3.max(root.descendants(), d => d._calculatedHeight) * 1.0]);
    treeLayout(root);

    let minX = 0, maxX = 0, minY = 0, maxY = 0;
    root.each(d => {
        const yTop = d.y - d._calculatedHeight / 2, yBottom = d.y + d._calculatedHeight / 2;
        const nodeWidth = d._calculatedWidth || MAIN_SHAPE_WIDTH;
        const xLeft = d.x - nodeWidth / 2, xRight = d.x + nodeWidth / 2;
        if (xLeft < minX) minX = xLeft; if (xRight > maxX) maxX = xRight;
        if (yTop < minY) minY = yTop; if (yBottom > maxY) maxY = yBottom;
    });
    const treeWidth = maxX - minX;
    let treeHeight = maxY - minY;

    let inputBlockHeight = 0;
    if (input) {
        inputBlockHeight = INPUT_BOX_HEIGHT + INPUT_TO_ROOT_SPACE;
    }

    const treeTranslateX = MARGIN.left - minX;
    const treeTranslateY = MARGIN.top - minY + inputBlockHeight;
    treeGroup.attr('transform', `translate(${treeTranslateX}, ${treeTranslateY})`);

    if (input) {
        const rootCoords = { x: root.x + treeTranslateX, y: root.y + treeTranslateY };
        const inputBoxY = rootCoords.y - INPUT_TO_ROOT_SPACE - INPUT_BOX_HEIGHT;
        const inputBox = svg.insert('g', '.decision-tree').attr('transform', `translate(${rootCoords.x - MAIN_SHAPE_WIDTH / 2}, ${inputBoxY})`);

        // Input box rectangle
        const inputRect = inputBox.append('rect').attr('width', MAIN_SHAPE_WIDTH).attr('height', INPUT_BOX_HEIGHT).attr('rx', 3).attr('fill', IO_BOX_FILLCOLOR).attr('stroke', IO_BOX_PENCOLOR).attr('stroke-width', BASE_PENWIDTH);

        // Add glow effect to input box when any leaf is highlighted (using input color) - same range as output!
        if (highlightUidSet.size > 0) {
            inputRect
                .style('filter', `
                    drop-shadow(0 0 8px rgba(253, 255, 182, 0.9))
                    drop-shadow(0 0 16px rgba(253, 255, 182, 0.7))
                    drop-shadow(0 0 28px rgba(253, 255, 182, 0.5))
                    drop-shadow(0 0 45px rgba(253, 255, 182, 0.3))
                    drop-shadow(0 0 65px rgba(253, 255, 182, 0.15))
                `)
                .attr('stroke', '#000000')
                .attr('stroke-width', 3);
        }

        // Truncate input text if too long
        const truncatedInput = truncateText(`"${input}"`, MAIN_SHAPE_WIDTH - 10); // Leave some padding
        inputBox.append('text')
            .attr('x', MAIN_SHAPE_WIDTH / 2)
            .attr('y', INPUT_BOX_HEIGHT / 2)
            .attr('text-anchor', 'middle')
            .attr('alignment-baseline', 'middle')
            .style('font-size', `${NODE_FONT_SIZE}px`)
            .style('font-weight', highlightUidSet.size > 0 ? 'bold' : 'normal')
            .style('fill', IO_BOX_TEXT_COLOR)
            .text(truncatedInput);

        svg.insert('line', '.decision-tree')
            .attr('x1', rootCoords.x)
            .attr('y1', inputBoxY + INPUT_BOX_HEIGHT)
            .attr('x2', rootCoords.x)
            .attr('y2', rootCoords.y - root._calculatedHeight / 2)
            .attr('stroke', ARROW_COLOR)
            .attr('stroke-width', highlightUidSet.size > 0 ? HIGHLIGHT_PENWIDTH_EDGE : BASE_PENWIDTH)
            .attr('stroke-dasharray', "4,4");
    }

    const finalSvgWidth = treeWidth + MARGIN.left + MARGIN.right;
    const finalSvgHeight = treeHeight + inputBlockHeight + MARGIN.top + MARGIN.bottom;
    svg.attr('width', finalSvgWidth).attr('height', finalSvgHeight);

    // Draw Links
    const isHighlightedEdge = (d) => highlightUidSet.has(d.source.data.uid) && highlightUidSet.has(d.target.data.uid);

    const link = treeGroup.selectAll('.link').data(root.links()).enter().append('g');
    link.append('line').attr('x1', d => d.source.x).attr('y1', d => d.source.y + d.source._calculatedHeight / 2).attr('x2', d => d.target.x).attr('y2', d => d.target.y - d.target._calculatedHeight / 2).attr('stroke', EDGE_COLOR).attr('stroke-width', d => isHighlightedEdge(d) ? HIGHLIGHT_PENWIDTH_EDGE : BASE_PENWIDTH).attr('marker-end', d => isHighlightedEdge(d) ? 'url(#arrowhead-highlight)' : 'url(#arrowhead)');

    // Draw Link Labels with support for custom routing keys
    const linkLabelGroup = link.append('g').attr('transform', d => `translate(${(d.source.x + d.target.x) / 2 + EDGE_LABEL_OFFSET_X}, ${(d.source.y + d.target.y) / 2})`);
    const linkLabelText = linkLabelGroup.append('text').attr('dy', EDGE_LABEL_OFFSET_Y).attr('text-anchor', 'middle').style('font-size', `${EDGE_FONT_SIZE}px`);

    linkLabelText.append('tspan').style('font-weight', d => isHighlightedEdge(d) ? 'bold' : 'normal').style('fill', d => {
        const edgeInfo = d.target.data._edge_info;
        if (edgeInfo?.is_true) return TRUE_LABEL_COLOR;
        if (edgeInfo?.is_false) return FALSE_LABEL_COLOR;
        return CUSTOM_LABEL_COLOR;
    }).text(d => {
        const edgeInfo = d.target.data._edge_info;
        if (edgeInfo?.is_true) return "True";
        if (edgeInfo?.is_false) return "False";
        return edgeInfo?.label || ''; // Show custom routing key
    });

    linkLabelText.clone(true).lower().attr('stroke', 'white').attr('stroke-width', 3).attr('stroke-linejoin', 'round');

    // Draw Nodes
    const node = treeGroup.selectAll('.node').data(root.descendants(), d => d.data.uid).enter().append('g')
        .attr('class', d => `node ${d.data.leaf ? 'node--leaf' : 'node--branch'}`)
        .attr('transform', d => `translate(${d.x},${d.y})`);

    // --- UPDATED: Node drawing logic now renders output boxes for leaves ---
    node.each(function (d) {
        const group = d3.select(this);
        const nodeData = d.data;
        const isHighlighted = highlightUidSet.has(nodeData.uid);
        const blockTopY = -d._calculatedHeight / 2;
        let currentY = blockTopY;
        let lastElementBottomY = 0; // To track where to connect lines from

        if (!nodeData.leaf) { // Branch Node
            const fill = isHighlighted ? BRANCH_HIGHLIGHT_FILLCOLOR : BRANCH_FILLCOLOR;
            const stroke = isHighlighted ? BRANCH_HIGHLIGHT_PENCOLOR : BRANCH_PENCOLOR;
            const penwidth = isHighlighted ? HIGHLIGHT_PENWIDTH_NODE : BASE_PENWIDTH;
            const nodeWidth = d._calculatedWidth || MAIN_SHAPE_WIDTH;
            const diamondCenterY = currentY + MAIN_SHAPE_HEIGHT / 2;
            const diamondPath = `M 0 ${currentY} L ${nodeWidth / 2} ${diamondCenterY} L 0 ${currentY + MAIN_SHAPE_HEIGHT} L ${-nodeWidth / 2} ${diamondCenterY} Z`;
            group.append('path').attr('d', diamondPath).attr('fill', fill).attr('stroke', stroke).attr('stroke-width', penwidth);

            // Truncate label if too long
            const truncatedLabel = truncateText(nodeData.label, nodeWidth - 10); // Leave some padding
            group.append('text').attr('x', 0).attr('y', diamondCenterY).attr('text-anchor', 'middle').attr('alignment-baseline', 'middle').style('font-size', `${NODE_FONT_SIZE}px`).style('font-weight', 'bold').style('fill', GLOBAL_TEXT_COLOR).text(truncatedLabel);
        } else { // Leaf Node
            const fill = isHighlighted ? LEAF_HIGHLIGHT_FILLCOLOR : LEAF_FILLCOLOR;
            const stroke = isHighlighted ? LEAF_HIGHLIGHT_PENCOLOR : LEAF_PENCOLOR;
            const nodeWidth = d._calculatedWidth || MAIN_SHAPE_WIDTH;
            group.append('rect').attr('x', -nodeWidth / 2).attr('y', currentY).attr('width', nodeWidth).attr('height', MAIN_SHAPE_HEIGHT).attr('rx', 3).attr('fill', fill).attr('stroke', stroke).attr('stroke-width', isHighlighted ? HIGHLIGHT_PENWIDTH_NODE : BASE_PENWIDTH);

            // Truncate type text if too long
            const truncatedTyp = truncateText(nodeData.typ || '', nodeWidth - 10); // Leave some padding
            group.append('text')
                .attr('x', 0)
                .attr('y', currentY + MAIN_SHAPE_HEIGHT / 2)
                .attr('text-anchor', 'middle')
                .attr('alignment-baseline', 'middle')
                .style('font-size', `${NODE_FONT_SIZE}px`)
                .style('font-weight', 'bold')
                .style('fill', GLOBAL_TEXT_COLOR)
                .text(truncatedTyp);

            lastElementBottomY = currentY + MAIN_SHAPE_HEIGHT;
            currentY += MAIN_SHAPE_HEIGHT;

            let examplesBottomY = lastElementBottomY;

            // NEW: Draw example boxes if they exist for this leaf (right after leaf)
            if (nodeData.examples && nodeData.examples.length > 0) {
                nodeData.examples.forEach((example, index) => {
                    const exampleBoxY = lastElementBottomY + (index === 0 ? 0 : 0); // No margin between stacked boxes
                    const exampleBox = group.append('g').attr('transform', `translate(${-nodeWidth / 2}, ${exampleBoxY})`);

                    // Truncate example text if too long
                    const maxExampleWidth = nodeWidth - 10; // Leave some padding
                    const truncatedExample = truncateText(`"${example}"`, maxExampleWidth);

                    exampleBox.append('rect')
                        .attr('width', nodeWidth).attr('height', INPUT_BOX_HEIGHT)
                        .attr('rx', 3).attr('fill', IO_BOX_FILLCOLOR).attr('stroke', IO_BOX_PENCOLOR)
                        .attr('stroke-width', isHighlighted ? HIGHLIGHT_PENWIDTH_EDGE : BASE_PENWIDTH);

                    exampleBox.append('text')
                        .attr('x', nodeWidth / 2).attr('y', INPUT_BOX_HEIGHT / 2)
                        .attr('text-anchor', 'middle').attr('alignment-baseline', 'middle')
                        .style('font-size', `${NODE_FONT_SIZE}px`).style('font-weight', 'bold').style('fill', IO_BOX_TEXT_COLOR)
                        .text(truncatedExample);

                    // Only add connecting line for first example box (from leaf to first example)
                    if (index === 0) {
                        group.append('line')
                            .attr('x1', 0).attr('y1', lastElementBottomY)
                            .attr('x2', 0).attr('y2', exampleBoxY)
                            .attr('stroke', ARROW_COLOR).attr('stroke-width', BASE_PENWIDTH)
                            .attr('stroke-dasharray', "4,4");
                    }

                    lastElementBottomY = exampleBoxY + INPUT_BOX_HEIGHT;
                });
                examplesBottomY = lastElementBottomY;
                currentY = lastElementBottomY - blockTopY;
            }

            if (nodeData.parser) {
                // Adjust parser position upward when examples exist
                let parserY;
                if (nodeData.examples && nodeData.examples.length > 0) {
                    parserY = currentY + LEAF_TO_PARSER_SPACE - 8; // Move up when examples exist
                } else {
                    parserY = currentY + LEAF_TO_PARSER_SPACE; // Normal position
                }

                // Calculate parser box width based on text content
                const MONO_CHAR_WIDTH_PARSER = PARSER_FONT_SIZE * 0.6;
                const parserTextWidth = nodeData.parser.length * MONO_CHAR_WIDTH_PARSER + 16; // Add padding
                const parserBoxWidth = Math.min(parserTextWidth, nodeWidth); // Don't exceed node width
                const parserX = -parserBoxWidth / 2;

                group.append('rect').attr('x', parserX).attr('y', parserY).attr('width', parserBoxWidth).attr('height', PARSER_BOX_HEIGHT).attr('rx', 2).attr('fill', isHighlighted ? PARSER_HIGHLIGHT_FILLCOLOR : PARSER_FILLCOLOR).attr('stroke', isHighlighted ? PARSER_HIGHLIGHT_PENCOLOR : PARSER_PENCOLOR).attr('stroke-width', isHighlighted ? HIGHLIGHT_PENWIDTH_NODE : BASE_PENWIDTH).attr('stroke-dasharray', "3,3");
                group.append('text').attr('x', 0).attr('y', parserY + PARSER_BOX_HEIGHT / 2).attr('text-anchor', 'middle').attr('alignment-baseline', 'middle').style('font-size', `${PARSER_FONT_SIZE}px`).style('font-weight', 'bold').style('fill', GLOBAL_TEXT_COLOR).text(nodeData.parser);

                // Connect from examples bottom (or leaf if no examples) to parser with ultra-short line
                const connectionStartY = examplesBottomY + 1; // Start extremely close to examples (quarter of original)
                const connectionEndY = parserY - 1; // End extremely close to parser (quarter of original)
                group.append('line')
                    .attr('x1', 0).attr('y1', connectionStartY)
                    .attr('x2', 0).attr('y2', connectionEndY)
                    .attr('stroke', isHighlighted ? EDGE_HIGHLIGHT_COLOR : PARSER_PENCOLOR).attr('stroke-width', isHighlighted ? HIGHLIGHT_PENWIDTH_EDGE : BASE_PENWIDTH).attr('stroke-dasharray', "3,3");

                lastElementBottomY = parserY + PARSER_BOX_HEIGHT;
                currentY = lastElementBottomY - blockTopY; // Adjust currentY based on total height so far
            }

            // NEW: Draw the output box if it exists for this leaf
            if (nodeData.output) {
                // Adjust output position downward when examples exist and increase distance 6x (double the previous 3x)
                let outputBoxY;
                const adjustedOutputSpace = LEAF_TO_OUTPUT_SPACE * 6; // 6x the original distance (double the previous 3x)
                if (nodeData.examples && nodeData.examples.length > 0) {
                    outputBoxY = lastElementBottomY + adjustedOutputSpace + 8; // Move down when examples exist + extra
                } else {
                    outputBoxY = lastElementBottomY + adjustedOutputSpace; // Normal position with 6x distance
                }

                // Parse output as type(value) format
                const match = nodeData.output.match(/^([^(]+)\(([^)]*)\)$/);

                // Calculate widths for type and value sections (declare outside for access in connection line)
                let totalWidth = 0;
                let boxHeight = OUTPUT_BOX_HEIGHT;
                let componentX = 0;
                let typeBoxWidth = 0;
                let valueBoxWidth = 0;
                let leftParenthesisWidth = 0;
                let spacing = 2;
                let typeText = '';
                let valueText = '';

                if (match) {
                    [, type, value] = match;
                    typeText = type;
                    valueText = value;

                    // Use monospace font for predictable width calculation
                    const MONO_CHAR_WIDTH = NODE_FONT_SIZE * 0.6; // Approximate width for monospace font

                    const getTextWidth = (text) => {
                        return text.length * MONO_CHAR_WIDTH;
                    };

                    const typeTextWidth = getTextWidth(typeText);
                    const valueTextWidth = getTextWidth(valueText);
                    leftParenthesisWidth = MONO_CHAR_WIDTH;
                    const rightParenthesisWidth = MONO_CHAR_WIDTH;
                    typeBoxWidth = typeTextWidth; // Type doesn't need truncation
                    valueBoxWidth = Math.min(valueTextWidth, MAX_VALUE_WIDTH); // Only value needs max width
                    // Update total width calculation for clean parentheses (no boxes)
                    totalWidth = typeBoxWidth + spacing + leftParenthesisWidth + spacing + valueBoxWidth + spacing + leftParenthesisWidth + spacing;
                    componentX = -totalWidth / 2;
                }

                // Create output box with calculated position
                const outputBox = group.append('g').attr('transform', `translate(${match ? componentX : -MAIN_SHAPE_WIDTH / 2}, ${outputBoxY})`);

                if (match) {
                    // Use previously calculated values (these are already calculated above)

                    // Truncate only value text if it's too long for the box (type doesn't need truncation)
                    const truncatedValueText = truncateText(valueText, MAX_VALUE_WIDTH - 2); // Use max width, not actual box width

                    // White background for the entire component - positioned at 0 since outputBox is already translated
                    const outputBgRect = outputBox.append('rect')
                        .attr('x', 0)
                        .attr('y', 0)
                        .attr('width', totalWidth)
                        .attr('height', boxHeight)
                        .attr('rx', 3)
                        .attr('fill', 'white')
                        .attr('stroke', IO_BOX_PENCOLOR)
                        .attr('stroke-width', isHighlighted ? HIGHLIGHT_PENWIDTH_EDGE * 2 : BASE_PENWIDTH); // Thicker border when highlighted

                    // Add enhanced highlight effect for output box with black border and value color glow
                    if (isHighlighted) {
                        // Black border with bold value-color glow effect - much larger range!
                        outputBgRect
                            .style('filter', `
                                drop-shadow(0 0 8px rgba(202, 255, 191, 0.9))
                                drop-shadow(0 0 16px rgba(202, 255, 191, 0.7))
                                drop-shadow(0 0 28px rgba(202, 255, 191, 0.5))
                                drop-shadow(0 0 45px rgba(202, 255, 191, 0.3))
                                drop-shadow(0 0 65px rgba(202, 255, 191, 0.15))
                            `)
                            .attr('stroke', '#000000')
                            .attr('stroke-width', 3);
                    }

                    // Type box (left side) - positioned at 0 since outputBox is already translated
                    const typeBox = outputBox.append('g');

                    typeBox.append('rect')
                        .attr('x', 0) // Start at 0 since outputBox handles positioning
                        .attr('y', 0)
                        .attr('width', typeBoxWidth)
                        .attr('height', boxHeight)
                        .attr('rx', 0) // No rounded corners on the right side
                        .attr('fill', LEAF_FILLCOLOR)
                        .attr('stroke', 'none'); // No internal border

                    typeBox.append('text')
                        .attr('x', typeBoxWidth / 2)
                        .attr('y', boxHeight / 2)
                        .attr('text-anchor', 'middle')
                        .attr('alignment-baseline', 'middle')
                        .style('font-size', `${NODE_FONT_SIZE}px`)
                        .style('font-weight', isHighlighted ? 'bold' : 'normal')
                        .style('fill', GLOBAL_TEXT_COLOR)
                        .text(typeText);

                    // Left parenthesis without background box - just text
                    outputBox.append('text')
                        .attr('x', typeBoxWidth + spacing)
                        .attr('y', boxHeight / 2)
                        .attr('text-anchor', 'start')
                        .attr('alignment-baseline', 'middle')
                        .style('font-size', `${NODE_FONT_SIZE}px`)
                        .style('font-weight', isHighlighted ? 'bold' : 'normal')
                        .style('fill', GLOBAL_TEXT_COLOR)
                        .text('(');

                    // Value box (right side) - positioned after left parenthesis
                    const valueBox = outputBox.append('g');
                    const valueX = typeBoxWidth + leftParenthesisWidth + spacing * 2; // Adjusted for no paren box

                    valueBox.append('rect')
                        .attr('x', valueX)
                        .attr('y', 0)
                        .attr('width', valueBoxWidth)
                        .attr('height', boxHeight)
                        .attr('rx', 0) // No rounded corners on the left side
                        .attr('fill', '#caffbf')
                        .attr('stroke', 'none'); // No internal border

                    valueBox.append('text')
                        .attr('x', valueX + valueBoxWidth / 2)
                        .attr('y', boxHeight / 2)
                        .attr('text-anchor', 'middle')
                        .attr('alignment-baseline', 'middle')
                        .style('font-size', `${NODE_FONT_SIZE}px`)
                        .style('font-weight', isHighlighted ? 'bold' : 'normal')
                        .style('fill', GLOBAL_TEXT_COLOR)
                        .text(truncatedValueText);

                    // Right parenthesis without background box - just text
                    const rightParenX = valueX + valueBoxWidth;
                    outputBox.append('text')
                        .attr('x', rightParenX + spacing)
                        .attr('y', boxHeight / 2)
                        .attr('text-anchor', 'start')
                        .attr('alignment-baseline', 'middle')
                        .style('font-size', `${NODE_FONT_SIZE}px`)
                        .style('font-weight', isHighlighted ? 'bold' : 'normal')
                        .style('fill', GLOBAL_TEXT_COLOR)
                        .text(')');
                } else {
                    // If not in type(value) format, display as plain text
                    outputBox.append('text')
                        .attr('x', MAIN_SHAPE_WIDTH / 2)
                        .attr('y', OUTPUT_BOX_HEIGHT / 2)
                        .attr('text-anchor', 'middle')
                        .attr('alignment-baseline', 'middle')
                        .style('font-size', `${NODE_FONT_SIZE}px`)
                        .style('font-weight', 'bold')
                        .style('fill', IO_BOX_TEXT_COLOR)
                        .text(nodeData.output);
                }

                // Connector line from the last element (leaf or parser) to the output box center - make it longer
                if (match) {
                    // For type(value) format, connect to component center
                    // OutputBox is already translated by componentX, so we connect to componentX + totalWidth/2
                    const componentCenterX = componentX + totalWidth / 2; // Center of the component
                    // Extend the line further down to make it longer
                    group.append('line')
                        .attr('x1', 0).attr('y1', lastElementBottomY)
                        .attr('x2', componentCenterX).attr('y2', outputBoxY - 5) // Connect slightly above component to extend line
                        .attr('stroke', ARROW_COLOR).attr('stroke-width', isHighlighted ? HIGHLIGHT_PENWIDTH_EDGE : BASE_PENWIDTH)
                        .attr('stroke-dasharray', "4,4");
                } else {
                    // For plain text format, connect to center - extend line
                    group.append('line')
                        .attr('x1', 0).attr('y1', lastElementBottomY)
                        .attr('x2', 0).attr('y2', outputBoxY - 5) // Connect slightly above to extend line
                        .attr('stroke', ARROW_COLOR).attr('stroke-width', isHighlighted ? HIGHLIGHT_PENWIDTH_EDGE : BASE_PENWIDTH)
                        .attr('stroke-dasharray', "4,4");
                }
            }
        }
    });

    console.log(body.select('svg').node().outerHTML);

} catch (error) {
    console.error("Error during SVG generation:", error);
    process.exit(1);
}