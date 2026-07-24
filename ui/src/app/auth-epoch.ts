export class AuthenticationEpoch {
  #value = 0;

  capture(): number {
    return this.#value;
  }

  invalidate(): number {
    this.#value += 1;
    return this.#value;
  }

  isCurrent(captured: number): boolean {
    return captured === this.#value;
  }
}

export const authenticationEpoch = new AuthenticationEpoch();
