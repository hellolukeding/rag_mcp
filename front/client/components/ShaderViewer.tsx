// components/AnimatedShader.jsx
'use client';

import { OrthographicCamera } from '@react-three/drei';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import { Mesh, ShaderMaterial } from 'three';

function ShaderPlane() {
    const meshRef = useRef<Mesh>(null);
    const viewport = useThree((state) => state.viewport);
    const uniforms = useMemo(() => ({
        iTime: { value: 0 },
        iResolution: { value: [1, 1, 1] },
    }), []);

    useFrame((state) => {
        if (meshRef.current) {
            (meshRef.current.material as ShaderMaterial).uniforms.iTime.value = state.clock.elapsedTime;
        }
    });

    const fragmentShader = `
    #define SPIN_ROTATION -2.0
    #define SPIN_SPEED 7.0
    #define OFFSET vec2(0.0)
    #define COLOUR_1 vec4(0.871, 0.267, 0.231, 1.0)
    #define COLOUR_2 vec4(0.0, 0.42, 0.706, 1.0)
    #define COLOUR_3 vec4(0.086, 0.137, 0.145, 1.0)
    #define CONTRAST 3.5
    #define LIGTHING 0.4
    #define SPIN_AMOUNT 0.25
    #define PIXEL_FILTER 745.0
    #define SPIN_EASE 1.0
    #define PI 3.14159265359
    #define IS_ROTATE false

    varying vec2 vUv;
    uniform vec3 iResolution;
    uniform float iTime;

    vec4 effect(vec2 screenSize, vec2 screen_coords) {
        float pixel_size = length(screenSize.xy) / PIXEL_FILTER;
        vec2 uv = (floor(screen_coords.xy*(1./pixel_size))*pixel_size - 0.5*screenSize.xy)/length(screenSize.xy) - OFFSET;
        float uv_len = length(uv);
        
        float speed = (SPIN_ROTATION*SPIN_EASE*0.2);
        if(IS_ROTATE){
           speed = iTime * speed;
        }
        speed += 302.2;
        float new_pixel_angle = atan(uv.y, uv.x) + speed - SPIN_EASE*20.*(1.*SPIN_AMOUNT*uv_len + (1. - 1.*SPIN_AMOUNT));
        vec2 mid = (screenSize.xy/length(screenSize.xy))/2.;
        uv = (vec2((uv_len * cos(new_pixel_angle) + mid.x), (uv_len * sin(new_pixel_angle) + mid.y)) - mid);
        
        uv *= 30.;
        speed = iTime*(SPIN_SPEED);
        vec2 uv2 = vec2(uv.x+uv.y);
        
        for(int i=0; i < 5; i++) {
            uv2 += sin(max(uv.x, uv.y)) + uv;
            uv  += 0.5*vec2(cos(5.1123314 + 0.353*uv2.y + speed*0.131121),sin(uv2.x - 0.113*speed));
            uv  -= 1.0*cos(uv.x + uv.y) - 1.0*sin(uv.x*0.711 - uv.y);
        }
        
        float contrast_mod = (0.25*CONTRAST + 0.5*SPIN_AMOUNT + 1.2);
        float paint_res = min(2., max(0.,length(uv)*(0.035)*contrast_mod));
        float c1p = max(0.,1. - contrast_mod*abs(1.-paint_res));
        float c2p = max(0.,1. - contrast_mod*abs(paint_res));
        float c3p = 1. - min(1., c1p + c2p);
        float light = (LIGTHING - 0.2)*max(c1p*5. - 4., 0.) + LIGTHING*max(c2p*5. - 4., 0.);
        return (0.3/CONTRAST)*COLOUR_1 + (1. - 0.3/CONTRAST)*(COLOUR_1*c1p + COLOUR_2*c2p + vec4(c3p*COLOUR_3.rgb, c3p*COLOUR_1.a)) + light;
    }

    void main() {
        vec2 fragCoord = vUv * iResolution.xy;
        gl_FragColor = effect(iResolution.xy, fragCoord);
    }
  `;

    const vertexShader = `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `;

    return (
        <mesh ref={meshRef} scale={[viewport.width, viewport.height, 1]}>
            <planeGeometry args={[1, 1]} />
            <shaderMaterial
                uniforms={uniforms}
                fragmentShader={fragmentShader}
                vertexShader={vertexShader}
                onUpdate={(self) => {
                    self.uniforms.iResolution.value = [window.innerWidth, window.innerHeight, 1];
                }}
            />
        </mesh>
    );
}

export default function AnimatedShader({ className = '' }) {
    return (
        <div className={`w-full h-full ${className}`}>
            <Canvas
                style={{ width: '100%', height: '100%' }}
                onCreated={({ gl }) => {
                    gl.setPixelRatio(window.devicePixelRatio);
                }}
            >
                <OrthographicCamera makeDefault position={[0, 0, 5]} zoom={100} />
                <ShaderPlane />
            </Canvas>
        </div>
    );
}