/// <reference types="astro/client" />
/// <reference types="@astrojs/svelte" />

declare module "*.svelte" {
    const component: any;
    export default component;
}