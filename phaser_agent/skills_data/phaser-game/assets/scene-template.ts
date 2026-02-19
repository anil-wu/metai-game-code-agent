import Phaser from 'phaser';

export interface SceneConfig {
    key: string;
    preload?: () => void;
    create?: () => void;
    update?: (time: number, delta: number) => void;
}

export abstract class BaseScene extends Phaser.Scene {
    protected sceneConfig: SceneConfig;

    constructor(config: SceneConfig) {
        super({ key: config.key });
        this.sceneConfig = config;
    }

    preload(): void {
        this.loadAssets();
        if (this.sceneConfig.preload) {
            this.sceneConfig.preload();
        }
    }

    create(): void {
        this.setupScene();
        if (this.sceneConfig.create) {
            this.sceneConfig.create();
        }
    }

    update(time: number, delta: number): void {
        this.updateScene(time, delta);
        if (this.sceneConfig.update) {
            this.sceneConfig.update(time, delta);
        }
    }

    protected abstract loadAssets(): void;
    protected abstract setupScene(): void;
    protected abstract updateScene(time: number, delta: number): void;
}

export class GameScene extends BaseScene {
    private player!: Phaser.Physics.Arcade.Sprite;
    private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;

    constructor() {
        super({ key: 'GameScene' });
    }

    protected loadAssets(): void {
        this.load.image('player', 'assets/player.png');
        this.load.image('background', 'assets/background.png');
    }

    protected setupScene(): void {
        this.add.image(400, 300, 'background');
        
        this.player = this.physics.add.sprite(100, 450, 'player');
        this.player.setCollideWorldBounds(true);
        
        if (this.input.keyboard) {
            this.cursors = this.input.keyboard.createCursorKeys();
        }
    }

    protected updateScene(time: number, delta: number): void {
        if (!this.cursors) return;

        if (this.cursors.left.isDown) {
            this.player.setVelocityX(-160);
        } else if (this.cursors.right.isDown) {
            this.player.setVelocityX(160);
        } else {
            this.player.setVelocityX(0);
        }

        if (this.cursors.up.isDown && this.player.body?.touching.down) {
            this.player.setVelocityY(-330);
        }
    }
}
