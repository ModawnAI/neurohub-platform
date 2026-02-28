declare module "@niivue/niivue" {
  export class Niivue {
    constructor(opts?: Record<string, unknown>);
    attachToCanvas(canvas: HTMLCanvasElement): void;
    loadVolumes(volumes: { url: string; colormap?: string; opacity?: number }[]): Promise<void>;
    addVolumeFromUrl(opts: { url: string; colormap?: string; opacity?: number }): Promise<void>;
  }
}
