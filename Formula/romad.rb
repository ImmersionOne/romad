class Romad < Formula
  include Language::Python::Virtualenv

  desc "Travel networking toolkit for digital nomads"
  homepage "https://github.com/ImmersionOne/romad"
  url "https://github.com/ImmersionOne/romad/archive/refs/tags/v0.4.0.tar.gz"
  sha256 "0019dfc4b32d63c1392aa264aed2253c1e0c2fb09216f8e2cc269bbfb8bb49b5"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "romad", shell_output("#{bin}/romad --version")
  end
end
