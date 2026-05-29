import Component from '../js/component.js';

export default class ToastNotification extends Component {
    constructor() {
        super();
        this.state = {
            toasts: []
        };
        
        // Expose a global way to show toasts
        window.showToast = this.show.bind(this);
    }

    show(message, type = 'info', duration = 3000) {
        const id = Date.now().toString() + Math.random().toString();
        const newToast = { id, message, type };
        
        this.setState({ toasts: [...this.state.toasts, newToast] });
        
        setTimeout(() => {
            this.remove(id);
        }, duration);
    }

    remove(id) {
        this.setState({
            toasts: this.state.toasts.filter(t => t.id !== id)
        });
    }

    render() {
        const { toasts } = this.state;
        
        if (!toasts || toasts.length === 0) return `<div class="toast-container empty"></div>`;
        
        return `
            <div class="toast-container">
                ${toasts.map(toast => `
                    <div class="toast toast-${toast.type} animate-toast-in">
                        <div class="toast-icon">
                            ${toast.type === 'error' ? '<i class="fas fa-exclamation-circle"></i>' : 
                              toast.type === 'success' ? '<i class="fas fa-check-circle"></i>' : 
                              '<i class="fas fa-info-circle"></i>'}
                        </div>
                        <div class="toast-message">${toast.message}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }
}
