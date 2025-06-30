import { mount } from 'svelte'
import App from './App.svelte'
// Removed import for app.css as Tailwind CSS is loaded via CDN

const app = mount(App, {
  target: document.getElementById('app'),
})

export default app