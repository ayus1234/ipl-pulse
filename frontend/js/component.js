/**
 * Base Component Class for Vanilla JS Reactive UI
 */
export default class Component {
    constructor(props = {}) {
        this.props = props;
        this.state = {};
        this.element = null;
    }

    // Update internal state and trigger re-render
    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.update();
    }

    // Must be implemented by subclasses
    render() {
        return '';
    }

    // Attach event listeners
    bindEvents() {
        // To be implemented by subclasses
    }

    // Mount the component to a parent element
    mount(parentElement) {
        // Create a temporary wrapper to parse the HTML string
        const wrapper = document.createElement('div');
        wrapper.innerHTML = this.render().trim();
        this.element = wrapper.firstChild;
        
        parentElement.appendChild(this.element);
        this.bindEvents();
        
        return this.element;
    }

    // Update the DOM efficiently (simplified diffing)
    update() {
        if (!this.element) return;
        
        const wrapper = document.createElement('div');
        wrapper.innerHTML = this.render().trim();
        const newElement = wrapper.firstChild;
        
        // Simple replacement for now (in a real app, use virtual DOM diffing)
        this.element.replaceWith(newElement);
        this.element = newElement;
        this.bindEvents();
    }
}
