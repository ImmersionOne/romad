class Romad < Formula
  include Language::Python::Virtualenv

  desc "Travel networking toolkit for digital nomads"
  homepage "https://github.com/ImmersionOne/romad"
  url "https://github.com/ImmersionOne/romad/archive/refs/tags/v0.9.0.tar.gz"
  sha256 "cedf517847443b85bf91fbe0158fb0b5078e79b4fc7c048fa99964e86894528d"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "romad", shell_output("#{bin}/romad --version")
  end
end
