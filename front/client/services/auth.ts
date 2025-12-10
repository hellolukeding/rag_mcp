import { API_BASE_URL } from './config';

export interface CaptchaStartResponse {
    session_id: string;
    expires_at?: string;
}

export const startCaptcha = async (): Promise<CaptchaStartResponse> => {
    const resp = await fetch(`${API_BASE_URL}/auth/captcha/start`, {
        method: 'POST'
    });
    if (!resp.ok) throw new Error('Failed to start captcha');
    return resp.json();
};

export const submitCaptcha = async (session_id: string, events: any): Promise<{ session_id: string; verified: boolean }> => {
    const resp = await fetch(`${API_BASE_URL}/auth/captcha/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id, events })
    });
    if (!resp.ok) throw new Error('Failed to submit captcha');
    return resp.json();
};

export const startImageCaptcha = async (): Promise<{ session_id: string; image: string; expires_at?: string }> => {
    const resp = await fetch(`${API_BASE_URL}/auth/captcha/image/start`, {
        method: 'POST'
    });
    if (!resp.ok) throw new Error('Failed to start image captcha');
    return resp.json();
};

export const verifyImageCaptcha = async (session_id: string, answer: string): Promise<{ session_id: string; verified: boolean }> => {
    const resp = await fetch(`${API_BASE_URL}/auth/captcha/image/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id, answer })
    });
    if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`Image captcha verify failed: ${txt}`);
    }
    return resp.json();
};

export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export const login = async (username: string, password: string, captcha_session_id: string): Promise<LoginResponse> => {
    const resp = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, captcha_session_id })
    });
    if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`Login failed: ${txt}`);
    }
    return resp.json();
};
